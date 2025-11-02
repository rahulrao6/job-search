"""Service for managing job records in Supabase"""

from typing import Optional, Dict, Any
from uuid import UUID
from src.db.supabase_client import get_client
from src.db.models import JobRecord


class JobService:
    """Service for job record operations"""
    
    @staticmethod
    def get_or_create_job(
        user_id: Optional[UUID],
        company_name: str,
        job_title: str,
        company_domain: Optional[str] = None,
        location: Optional[str] = None,
        department: Optional[str] = None,
        source_url: Optional[str] = None,
        job_data: Optional[Dict[str, Any]] = None
    ) -> JobRecord:
        """
        Get existing job or create new one.
        
        Args:
            user_id: User UUID (optional)
            company_name: Company name
            job_title: Job title
            company_domain: Company domain (optional)
            location: Job location (optional)
            department: Department (optional)
            source_url: Source URL (optional)
            job_data: Additional job data to store in scraped_data (optional)
            
        Returns:
            JobRecord
        """
        client = get_client()
        
        # Try to find existing job
        query = client.table('jobs').select('*').eq('company_name', company_name).eq('job_title', job_title)
        
        if user_id:
            query = query.eq('user_id', str(user_id))
        else:
            query = query.is_('user_id', 'null')
        
        result = query.execute()
        
        if result.data:
            # Found existing job
            return JobRecord(**result.data[0])
        
        # Create new job
        job_data_dict = {
            'company_name': company_name,
            'job_title': job_title,
            'status': 'active'
        }
        
        if user_id:
            job_data_dict['user_id'] = str(user_id)
        if company_domain:
            job_data_dict['company_domain'] = company_domain
        if location:
            job_data_dict['location'] = location
        if department:
            job_data_dict['department'] = department
        if source_url:
            job_data_dict['source_url'] = source_url
        if job_data:
            job_data_dict['scraped_data'] = job_data
            # Extract common fields from job_data
            if 'required_skills' in job_data:
                job_data_dict['required_skills'] = job_data['required_skills']
            if 'nice_to_have_skills' in job_data:
                job_data_dict['nice_to_have_skills'] = job_data['nice_to_have_skills']
            if 'experience_required' in job_data:
                job_data_dict['experience_required'] = job_data['experience_required']
            if 'education_required' in job_data:
                job_data_dict['education_required'] = job_data['education_required']
        
        insert_result = client.table('jobs').insert(job_data_dict).execute()
        
        if insert_result.data:
            return JobRecord(**insert_result.data[0])
        
        raise Exception("Failed to create job record")
    
    @staticmethod
    def get_job_by_id(job_id: UUID) -> Optional[JobRecord]:
        """Get job by ID"""
        client = get_client()
        
        result = client.table('jobs').select('*').eq('id', str(job_id)).execute()
        
        if result.data:
            return JobRecord(**result.data[0])
        
        return None
    
    @staticmethod
    def update_job(job_id: UUID, updates: Dict[str, Any]) -> JobRecord:
        """Update job record"""
        client = get_client()
        
        result = client.table('jobs').update(updates).eq('id', str(job_id)).execute()
        
        if result.data:
            return JobRecord(**result.data[0])
        
        raise Exception("Failed to update job record")

