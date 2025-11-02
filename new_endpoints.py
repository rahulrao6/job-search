@api.route('/resume/upload', methods=['POST'])
@require_auth
@handle_exceptions
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
        
        # Update user profile with resume data
        client = get_client()
        resume_parsed_data = {
            'skills': profile.skills,
            'past_companies': profile.past_companies,
            'schools': profile.schools,
            'current_title': profile.current_title,
            'years_experience': None  # Could extract from company_tenures if needed
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
                'message': 'Resume uploaded and parsed successfully'
            }
        }), 200
        
    except Exception as e:
        print(f"Error in resume upload: {e}")
        import traceback
        traceback.print_exc()
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
        print(f"Error parsing job: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': {
                'code': 'PARSING_ERROR',
                'message': f'Failed to parse job posting: {str(e)}',
                'details': {}
            }
        }), 500

