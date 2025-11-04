"""REST API routes for connection finder"""

import logging
import time
from datetime import datetime
from typing import Optional
from flask import Blueprint, request, jsonify

from uuid import UUID, uuid4
from src.api.auth import require_auth, optional_auth
from src.api.middleware import handle_exceptions
from src.api.schemas import (
    SearchRequest, SearchResponse, ErrorResponse, HealthResponse,
    QuotaResponse, ProfileResponse, format_search_response
)
from src.core.orchestrator import ConnectionFinder
from src.models.job_context import CandidateProfile, JobContext
from src.models.person import PersonCategory
from src.services.job_service import JobService
from src.services.discovery_service import DiscoveryService
from src.services.user_service import UserService
from src.db.supabase_client import get_client, health_check as db_health_check
from src.db.models import UserProfile
from src.extractors.resume_parser import ResumeParser
from src.extractors.job_parser import JobParser
from src.utils.storage import upload_resume_to_storage, get_resume_from_storage
from src.utils.logger import log_request
from src.utils.metrics import get_metrics_tracker
from src.utils.cache import get_cache
from werkzeug.utils import secure_filename
import os
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

logger = logging.getLogger(__name__)
api = Blueprint('api', __name__, url_prefix='/api/v1')


@api.route('/health', methods=['GET'])
@handle_exceptions
def health():
    """Health check endpoint with detailed status"""
    # Check database connection
    db_status = db_health_check()
    
    # Check source configurations with more details
    google_cse_id = os.getenv('GOOGLE_CSE_ID')
    google_api_key = os.getenv('GOOGLE_API_KEY')
    github_token = os.getenv('GITHUB_TOKEN')
    openai_key = os.getenv('OPENAI_API_KEY')
    
    sources_status = {
        'google_cse': {
            'configured': bool(google_cse_id and google_api_key),
            'has_cse_id': bool(google_cse_id),
            'has_api_key': bool(google_api_key),
            'remaining_quota': None  # Would need to query Google API
        },
        'github': {
            'configured': bool(github_token),
            'has_token': bool(github_token),
            'rate_limit_remaining': None  # Would need to check GitHub API
        },
        'openai': {
            'configured': bool(openai_key),
            'has_key': bool(openai_key),
            'key_format_valid': bool(openai_key and openai_key.startswith('sk-')) if openai_key else False
        }
    }
    
    # Get cache statistics
    try:
        cache = get_cache()
        cache_stats = cache.get_stats()
    except Exception as e:
        logger.warning(f"Error getting cache stats: {e}", exc_info=True)
        cache_stats = {'error': str(e)}
    
    # Get basic metrics
    try:
        metrics_tracker = get_metrics_tracker()
        metrics_summary = {
            'total_requests': metrics_tracker.get_stats().get('total_requests', 0),
            'total_errors': metrics_tracker.get_stats().get('total_errors', 0),
            'recent_requests': metrics_tracker.get_stats().get('recent_requests', 0)
        }
    except Exception as e:
        logger.warning(f"Error getting metrics: {e}", exc_info=True)
        metrics_summary = {'error': str(e)}
    
    # Determine overall status
    all_critical_configured = db_status['connected'] and bool(google_cse_id and google_api_key)
    status = 'healthy' if all_critical_configured else 'degraded'
    
    response_data = {
        'status': status,
        'sources': sources_status,
        'database': db_status,
        'cache': cache_stats,
        'metrics': metrics_summary
    }
    
    return jsonify(response_data)


@api.route('/metrics', methods=['GET'])
@handle_exceptions
def metrics():
    """Get application metrics"""
    metrics_tracker = get_metrics_tracker()
    cache = get_cache()
    
    metrics_data = metrics_tracker.get_stats()
    cache_stats = cache.get_stats()
    
    return jsonify({
        'success': True,
        'data': {
            'api_metrics': metrics_data,
            'cache': cache_stats,
            'timestamp': datetime.utcnow().isoformat()
        }
    }), 200


@api.route('/search', methods=['POST'])
@require_auth
@handle_exceptions
@log_request
def search():
    """
    Main search endpoint with profile context.
    
    Request body:
    {
        "company": "Stripe",
        "job_title": "Software Engineer",
        "profile": {
            "skills": ["Python", "Go"],
            "past_companies": ["Google"],
            "schools": ["Stanford"]
        },
        "filters": {
            "categories": ["recruiter", "manager"],
            "min_confidence": 0.7
        }
    }
    """
    # Get user context from auth middleware
    user_context = request.user_context
    
    try:
        # Parse and validate request
        body = request.get_json()
        if not body:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_REQUEST',
                    'message': 'Request body is required',
                    'details': {}
                }
            }), 400
        # Extract search parameters
        company = body.get('company') or body.get('search', {}).get('company')
        job_title = body.get('job_title') or body.get('job_title') or body.get('search', {}).get('job_title')
        
        if not company or not job_title:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_REQUEST',
                    'message': 'company and job_title are required',
                    'details': {}
                }
            }), 400
        
        # Auto-load user's saved resume data if no profile provided
        profile_data = body.get('profile') or {}
        client = get_client()
        
        # Try to load saved resume data from profile
        saved_resume_data = None
        if not profile_data or not any([profile_data.get('skills'), profile_data.get('past_companies'), profile_data.get('schools')]):
            try:
                profile_result = client.table('profiles').select('resume_parsed_data').eq('id', str(user_context.user_id)).execute()
                if profile_result.data and profile_result.data[0].get('resume_parsed_data'):
                    saved_resume_data = profile_result.data[0]['resume_parsed_data']
            except Exception as e:
                logger.warning(f"Error loading saved resume data: {e}", exc_info=True)
        
        # Use provided profile data or fallback to saved resume data
        skills = (body.get('skills') or profile_data.get('skills') or 
                 (saved_resume_data.get('skills') if saved_resume_data else []) or [])
        past_companies = (body.get('past_companies') or profile_data.get('past_companies') or 
                         (saved_resume_data.get('past_companies') if saved_resume_data else []) or [])
        schools = (body.get('schools') or profile_data.get('schools') or 
                  (saved_resume_data.get('schools') if saved_resume_data else []) or [])
        current_title = (body.get('current_title') or profile_data.get('current_title') or 
                        (saved_resume_data.get('current_title') if saved_resume_data else None))
        years_experience = (body.get('years_experience') or profile_data.get('years_experience') or 
                           (saved_resume_data.get('years_experience') if saved_resume_data else None))
        
        # Extract job context
        job_url = body.get('job_url') or body.get('job_context', {}).get('job_url')
        job_description = body.get('job_description') or body.get('job_context', {}).get('job_description')
        required_skills = body.get('required_skills') or body.get('job_context', {}).get('required_skills')
        department = body.get('department') or body.get('search', {}).get('department')
        location = body.get('location') or body.get('search', {}).get('location')
        company_domain = body.get('company_domain') or body.get('search', {}).get('company_domain')
        
        # Auto-scrape job if job_url provided without job_description
        if job_url and not job_description:
            try:
                job_parser = JobParser()
                job_data = job_parser.parse(job_url, auto_fetch=True)
                
                # Use parsed data to fill in missing fields
                if not company and job_data.get('company'):
                    company = job_data.get('company')
                if not job_title and job_data.get('job_title'):
                    job_title = job_data.get('job_title')
                if not department and job_data.get('department'):
                    department = job_data.get('department')
                if not location and job_data.get('location'):
                    location = job_data.get('location')
                if not company_domain and job_data.get('company_domain'):
                    company_domain = job_data.get('company_domain')
                if not required_skills and job_data.get('required_skills'):
                    required_skills = job_data.get('required_skills')
                if not job_description and job_data.get('job_description'):
                    job_description = job_data.get('job_description')
            except Exception as e:
                logger.warning(f"Error auto-scraping job URL: {e}", exc_info=True)
                # Continue with provided data only
        
        # Extract filters
        filters = body.get('filters', {})
        categories_filter = filters.get('categories') or body.get('categories')
        min_confidence = filters.get('min_confidence') or body.get('min_confidence')
        max_results = filters.get('max_results') or body.get('max_results')
        
        # Build user profile
        user_profile = None
        if skills or past_companies or schools or current_title:
            user_profile = CandidateProfile(
                skills=skills,
                past_companies=past_companies,
                schools=schools,
                current_title=current_title,
                company_tenures={}  # Not provided
            )
        
        # Build job context
        job_context = None
        if job_url or job_description:
            # Extract candidate info from profile if available
            candidate_schools_from_profile = schools or []
            candidate_past_companies_from_profile = past_companies or []
            candidate_skills_from_profile = skills or []
            
            job_context = JobContext(
                job_url=job_url or "",
                job_text=job_description,
                company=company,
                job_title=job_title,
                department=department,
                location=location,
                company_domain=company_domain,
                candidate_skills=required_skills or candidate_skills_from_profile,
                candidate_schools=candidate_schools_from_profile,
                candidate_past_companies=candidate_past_companies_from_profile,
                candidate_resume=None  # Not required - profile data is used instead
            )
        
        # Track timing
        start_time = time.time()
        
        # Get or create job record
        job_record = None
        try:
            job_record = JobService.get_or_create_job(
                user_id=user_context.user_id,
                company_name=company,
                job_title=job_title,
                company_domain=company_domain,
                location=location,
                department=department,
                source_url=job_url,
                job_data={
                    'required_skills': required_skills,
                    'description': job_description
                } if required_skills or job_description else None
            )
        except Exception as e:
            logger.warning(f"Error creating job record: {e}", exc_info=True)
            # Continue without job record
        
        # Run search
        finder = ConnectionFinder()
        results = finder.find_connections_with_context(
            company=company,
            title=job_title,
            user_profile=user_profile,
            job_context=job_context,
            company_domain=company_domain,
            use_cache=True,
            filters=filters
        )
        
        # Save discoveries to database
        all_people_dicts = []
        for category, people_list in results.get('by_category', {}).items():
            all_people_dicts.extend(people_list)
        
        # Extract relevance scores and match reasons
        relevance_scores = {}
        match_reasons_dict = {}
        for person_dict in all_people_dicts:
            person_name = person_dict.get('name', '')
            if 'relevance_score' in person_dict:
                relevance_scores[person_name] = person_dict['relevance_score']
            if 'match_reasons' in person_dict:
                match_reasons_dict[person_name] = person_dict.get('match_reasons', [])
        
        # Convert dicts back to Person objects for saving
        from src.models.person import Person as PersonModel
        people_objects = []
        for person_dict in all_people_dicts:
            try:
                person_obj = PersonModel(
                    name=person_dict.get('name', ''),
                    title=person_dict.get('title'),
                    company=person_dict.get('company', company),
                    linkedin_url=person_dict.get('linkedin_url'),
                    email=person_dict.get('email'),
                    source=person_dict.get('source', 'unknown'),
                    confidence_score=person_dict.get('confidence', 0.5),
                    department=person_dict.get('department'),
                    location=person_dict.get('location'),
                    skills=person_dict.get('skills', []),
                    category=PersonCategory(person_dict.get('category', 'unknown'))
                )
                people_objects.append(person_obj)
            except Exception as e:
                logger.warning(f"Error converting person dict to Person object: {e}", exc_info=True)
                continue
        
        # Save discoveries
        discoveries_saved = []
        if job_record and people_objects:
            try:
                discoveries_saved = DiscoveryService.save_discoveries(
                    job_id=job_record.id,
                    user_id=user_context.user_id,
                    people=people_objects,
                    relevance_scores=relevance_scores,
                    match_reasons=match_reasons_dict
                )
                if discoveries_saved:
                    logger.info(f"Saved {len(discoveries_saved)} discoveries for job {job_record.id}")
                else:
                    logger.warning(f"No discoveries saved for job {job_record.id} (had {len(people_objects)} people)")
            except Exception as e:
                logger.error(f"Error saving discoveries: {e}", exc_info=True)
                # Don't fail the entire request if discovery saving fails
        
        # Calculate timing
        search_time_ms = int((time.time() - start_time) * 1000)
        
        # Increment user usage (quota)
        UserService.increment_usage(user_context.user_id)
        
        # Increment rate limit counter for successful request
        if hasattr(request, '_rate_limit_checked') and request._rate_limit_checked:
            UserService.increment_rate_limit(user_context.user_id)
        
        # Format response
        response_data = format_search_response(
            results=results,
            search_id=str(uuid4()) if job_record else None,
            timing={
                'search_time_ms': search_time_ms,
                'sources_used': list(results.get('source_stats', {}).get('by_source', {}).keys()),
                'paid_sources_used': False  # Would check actual sources used
            },
            cost=results.get('cost_stats', {})
        )
        
        # Add quota info
        quota_info = UserService.get_user_quota(user_context.user_id)
        response_data['data']['quota'] = quota_info
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error in search endpoint: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_SERVER_ERROR',
                'message': str(e),
                'details': {}
            }
        }), 500


@api.route('/quota', methods=['GET'])
@require_auth
@handle_exceptions
@log_request
def quota():
    """Get remaining quota for user"""
    user_context = request.user_context
    
    quota_info = UserService.get_user_quota(user_context.user_id)
    
    return jsonify({
        'success': True,
        'data': quota_info
    }), 200


@api.route('/connections/<connection_id>', methods=['GET'])
@require_auth
@handle_exceptions
@log_request
def get_connection(connection_id: str):
    """Get details for a specific connection"""
    user_context = request.user_context
    
    try:
        discovery_id = UUID(connection_id)
        discovery = DiscoveryService.get_discovery_by_id(discovery_id)
        
        if not discovery:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'NOT_FOUND',
                    'message': 'Connection not found',
                    'details': {'connection_id': connection_id}
                }
            }), 404
        
        # Convert to response format
        response_data = {
            'id': str(discovery.id),
            'name': discovery.full_name,
            'title': discovery.title,
            'company': discovery.company,
            'linkedin_url': discovery.linkedin_url,
            'email': discovery.email,
            'source': discovery.source,
            'confidence': discovery.confidence_score or 0.5,
            'relevance_score': discovery.relevance_score,
            'match_reasons': discovery.match_reasons or [],
            'category': discovery.person_type,
            'department': discovery.department,
            'location': discovery.location,
            'contacted': discovery.contacted
        }
        
        return jsonify({
            'success': True,
            'data': {
                'connection': response_data
            }
        }), 200
        
    except ValueError:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INVALID_REQUEST',
                'message': 'Invalid connection ID format',
                'details': {}
            }
        }), 400


@api.route('/profile', methods=['GET'])
@require_auth
@handle_exceptions
@log_request
def get_profile():
    """Get saved user profile"""
    user_context = request.user_context
    
    client = get_client()
    
    try:
        result = client.table('profiles').select('*').eq('id', str(user_context.user_id)).execute()
        
        if not result.data:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'NOT_FOUND',
                    'message': 'Profile not found',
                    'details': {}
                }
            }), 404
        
        profile_data = result.data[0]
        
        # Extract resume parsed data
        resume_data = profile_data.get('resume_parsed_data', {})
        
        return jsonify({
            'success': True,
            'data': {
                'profile': {
                    'id': profile_data['id'],
                    'email': profile_data['email'],
                    'full_name': profile_data.get('full_name'),
                    'linkedin_url': profile_data.get('linkedin_url'),
                    'resume_url': profile_data.get('resume_url'),
                    'skills': resume_data.get('skills', []),
                    'past_companies': resume_data.get('past_companies', []),
                    'schools': resume_data.get('schools', []),
                    'current_title': resume_data.get('current_title'),
                    'years_experience': resume_data.get('years_experience')
                }
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'DATABASE_ERROR',
                'message': f'Error fetching profile: {str(e)}',
                'details': {}
            }
        }), 500


@api.route('/profile/save', methods=['POST'])
@require_auth
@handle_exceptions
@log_request
def save_profile():
    """Save user profile"""
    user_context = request.user_context
    
    body = request.get_json()
    if not body or 'profile' not in body:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INVALID_REQUEST',
                'message': 'Profile data is required',
                'details': {}
            }
        }), 400
    
    profile_data = body['profile']
    
    client = get_client()
    
    try:
        # Update or create profile
        # Extract resume parsed data
        resume_parsed_data = {
            'skills': profile_data.get('skills', []),
            'past_companies': profile_data.get('past_companies', []),
            'schools': profile_data.get('schools', []),
            'current_title': profile_data.get('current_title'),
            'years_experience': profile_data.get('years_experience')
        }
        
        update_data = {
            'resume_parsed_data': resume_parsed_data
        }
        
        if 'full_name' in profile_data:
            update_data['full_name'] = profile_data['full_name']
        if 'linkedin_url' in profile_data:
            update_data['linkedin_url'] = profile_data['linkedin_url']
        if 'resume_url' in profile_data:
            update_data['resume_url'] = profile_data['resume_url']
        
        result = client.table('profiles').update(update_data).eq('id', str(user_context.user_id)).execute()
        
        if result.data:
            return jsonify({
                'success': True,
                'data': {
                    'profile_id': str(user_context.user_id),
                    'message': 'Profile saved successfully'
                }
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'NOT_FOUND',
                    'message': 'Profile not found',
                    'details': {}
                }
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': {
                'code': 'DATABASE_ERROR',
                'message': f'Error saving profile: {str(e)}',
                'details': {}
            }
        }), 500


@api.route('/resume/upload', methods=['POST'])
@require_auth
@handle_exceptions
@log_request
def upload_resume():
    """
    Upload and parse resume PDF.
    
    Accepts:
    - multipart/form-data with 'file' (PDF file)
    - OR JSON with 'resume_url' (Supabase Storage URL)
    
    Returns parsed resume data and saves to profile.
    """
    user_context = request.user_context
    
    try:
        resume_parser = ResumeParser()
        pdf_bytes = None
        resume_text = None
        resume_url = None
        
        # Check if file upload (multipart/form-data)
        if 'file' in request.files:
            file = request.files['file']
            
            if file.filename == '':
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'INVALID_REQUEST',
                        'message': 'No file provided',
                        'details': {}
                    }
                }), 400
            
            # Validate file type
            if not file.filename.lower().endswith('.pdf'):
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'INVALID_REQUEST',
                        'message': 'Only PDF files are supported',
                        'details': {}
                    }
                }), 400
            
            # Check file size (max 10MB)
            file.seek(0, 2)  # Seek to end
            file_size = file.tell()
            file.seek(0)  # Reset
            
            if file_size > 10 * 1024 * 1024:  # 10MB
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'INVALID_REQUEST',
                        'message': 'File size exceeds 10MB limit',
                        'details': {}
                    }
                }), 400
            
            # Read PDF bytes
            pdf_bytes = file.read()
            
            # Extract text from PDF
            resume_text = resume_parser.extract_text_from_pdf(pdf_bytes)
            
            # Upload to Supabase Storage
            filename = secure_filename(file.filename)
            resume_url = upload_resume_to_storage(
                user_id=user_context.user_id,
                pdf_bytes=pdf_bytes,
                filename=filename
            )
        
        # Check if URL provided (JSON)
        elif request.is_json:
            body = request.get_json()
            resume_url = body.get('resume_url')
            
            if not resume_url:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'INVALID_REQUEST',
                        'message': 'Either file or resume_url must be provided',
                        'details': {}
                    }
                }), 400
            
            # Download from Supabase Storage
            try:
                pdf_bytes = get_resume_from_storage(resume_url)
                resume_text = resume_parser.extract_text_from_pdf(pdf_bytes)
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'STORAGE_ERROR',
                        'message': f'Failed to fetch resume from storage: {str(e)}',
                        'details': {}
                    }
                }), 400
        else:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_REQUEST',
                    'message': 'Either file (multipart/form-data) or resume_url (JSON) must be provided',
                    'details': {}
                }
            }), 400
        
        # Parse resume text
        if not resume_text:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'PARSING_ERROR',
                    'message': 'Failed to extract text from PDF',
                    'details': {}
                }
            }), 400
        
        profile = resume_parser.parse(resume_text)
        
        # Check if AI was used (for debugging/feedback)
        ai_used = resume_parser.use_ai
        
        # Update user profile with resume data
        client = get_client()
        resume_parsed_data = {
            'skills': profile.skills,
            'past_companies': profile.past_companies,
            'schools': profile.schools,
            'current_title': getattr(profile, 'current_title', None),
            'years_experience': getattr(profile, 'years_experience', None)  # Extracted from AI parsing
        }
        
        update_data = {
            'resume_url': resume_url,
            'resume_parsed_data': resume_parsed_data
        }
        
        result = client.table('profiles').update(update_data).eq('id', str(user_context.user_id)).execute()
        
        if not result.data:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'NOT_FOUND',
                    'message': 'Profile not found',
                    'details': {}
                }
            }), 404
        
        return jsonify({
            'success': True,
            'data': {
                'resume_url': resume_url,
                'parsed_data': {
                    'skills': profile.skills,
                    'past_companies': profile.past_companies,
                    'schools': profile.schools,
                    'current_title': profile.current_title,
                    'years_experience': None
                },
                'ai_enhanced': ai_used,
                'message': 'Resume uploaded and parsed successfully'
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error in resume upload: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_SERVER_ERROR',
                'message': f'Error processing resume: {str(e)}',
                'details': {}
            }
        }), 500


@api.route('/job/parse', methods=['POST'])
@require_auth
@handle_exceptions
@log_request
def parse_job():
    """
    Parse job posting from URL.
    
    Request body:
    {
        "job_url": "https://..."
    }
    
    Automatically fetches and parses the job posting.
    """
    user_context = request.user_context
    
    body = request.get_json()
    if not body or 'job_url' not in body:
        return jsonify({
            'success': False,
            'error': {
                'code': 'INVALID_REQUEST',
                'message': 'job_url is required',
                'details': {}
            }
        }), 400
    
    job_url = body.get('job_url')
    
    if not job_url or not isinstance(job_url, str):
        return jsonify({
            'success': False,
            'error': {
                'code': 'INVALID_REQUEST',
                'message': 'job_url must be a valid URL string',
                'details': {}
            }
        }), 400
    
    try:
        # Parse job posting
        job_parser = JobParser()
        job_data = job_parser.parse(job_url, auto_fetch=True)
        
        return jsonify({
            'success': True,
            'data': {
                'job_url': job_url,
                'company': job_data.get('company'),
                'company_domain': job_data.get('company_domain'),
                'job_title': job_data.get('job_title'),
                'department': job_data.get('department'),
                'location': job_data.get('location'),
                'required_skills': job_data.get('required_skills', []),
                'job_description': job_data.get('job_description'),
                'seniority': job_data.get('seniority')
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error parsing job: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': {
                'code': 'PARSING_ERROR',
                'message': f'Failed to parse job posting: {str(e)}',
                'details': {}
            }
        }), 500

