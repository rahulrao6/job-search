"""Supabase Storage utilities for file uploads and downloads"""

import os
from typing import Optional
from datetime import datetime
from uuid import UUID
from src.db.supabase_client import get_client


def upload_resume_to_storage(user_id: UUID, pdf_bytes: bytes, filename: Optional[str] = None) -> str:
    """
    Upload resume PDF to Supabase Storage bucket 'resumes'.
    
    Args:
        user_id: User UUID
        pdf_bytes: PDF file as bytes
        filename: Optional custom filename (defaults to timestamped filename)
        
    Returns:
        Public URL of uploaded resume
        
    Raises:
        Exception: If upload fails
    """
    client = get_client()
    bucket_name = "resumes"
    
    # Generate filename if not provided
    if not filename:
        timestamp = int(datetime.now().timestamp() * 1000)
        filename = f"{timestamp}_resume.pdf"
    
    # Storage path: {user_id}/{filename}
    storage_path = f"{user_id}/{filename}"
    
    try:
        # Try to delete existing file first (ignore if doesn't exist) to achieve upsert behavior
        try:
            client.storage.from_(bucket_name).remove([storage_path])
        except Exception:
            # File doesn't exist, which is fine - we'll upload it
            pass
        
        # Upload file to storage
        # Supabase storage upload expects file content
        result = client.storage.from_(bucket_name).upload(
            path=storage_path,
            file=pdf_bytes,
            file_options={
                "content-type": "application/pdf"
            }
        )
        
        # Get public URL
        public_url = client.storage.from_(bucket_name).get_public_url(storage_path)
        
        return public_url
        
    except Exception as e:
        raise Exception(f"Failed to upload resume to storage: {str(e)}")


def get_resume_from_storage(resume_url: str) -> bytes:
    """
    Download resume PDF from Supabase Storage.
    
    Args:
        resume_url: Public URL of the resume
        
    Returns:
        PDF file as bytes
        
    Raises:
        Exception: If download fails
    """
    client = get_client()
    bucket_name = "resumes"
    
    try:
        # Extract path from URL
        # URL format: https://{project}.supabase.co/storage/v1/object/public/resumes/{user_id}/{filename}
        parts = resume_url.split("/storage/v1/object/public/resumes/")
        if len(parts) != 2:
            raise ValueError("Invalid resume URL format")
        
        storage_path = parts[1]
        
        # Download file
        response = client.storage.from_(bucket_name).download(storage_path)
        
        return response
        
    except Exception as e:
        raise Exception(f"Failed to download resume from storage: {str(e)}")


def delete_resume_from_storage(resume_url: str) -> bool:
    """
    Delete resume PDF from Supabase Storage.
    
    Args:
        resume_url: Public URL of the resume
        
    Returns:
        True if deleted successfully
        
    Raises:
        Exception: If deletion fails
    """
    client = get_client()
    bucket_name = "resumes"
    
    try:
        # Extract path from URL
        parts = resume_url.split("/storage/v1/object/public/resumes/")
        if len(parts) != 2:
            raise ValueError("Invalid resume URL format")
        
        storage_path = parts[1]
        
        # Delete file
        client.storage.from_(bucket_name).remove([storage_path])
        
        return True
        
    except Exception as e:
        raise Exception(f"Failed to delete resume from storage: {str(e)}")

