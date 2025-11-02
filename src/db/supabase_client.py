"""Supabase client for database operations"""

import os
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Global Supabase client singleton
_supabase_client: Optional[Client] = None


def get_client() -> Client:
    """Get or create Supabase client singleton"""
    global _supabase_client
    
    if _supabase_client is None:
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')  # Anon key for client-side operations
        
        if not supabase_url or not supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY must be set in environment variables"
            )
        
        _supabase_client = create_client(supabase_url, supabase_key)
    
    return _supabase_client


def get_client_with_token(token: str) -> Client:
    """
    Get Supabase client with user's JWT token.
    Use this when you need to make authenticated requests on behalf of a user.
    """
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_KEY must be set in environment variables"
        )
    
    # Create client and set session
    client = create_client(supabase_url, supabase_key)
    client.auth.set_session(token)
    
    return client


def health_check() -> dict:
    """Check Supabase connection health"""
    try:
        client = get_client()
        # Simple query to test connection
        result = client.table('profiles').select('id').limit(1).execute()
        return {
            'status': 'healthy',
            'connected': True,
            'message': 'Supabase connection successful'
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'connected': False,
            'message': f'Supabase connection failed: {str(e)}'
        }


def reset_client():
    """Reset client (useful for testing)"""
    global _supabase_client
    _supabase_client = None

