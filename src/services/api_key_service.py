"""API key validation and rate limiting service"""

import os
import time
import secrets
import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from src.db.supabase_client import get_client
from src.db.models import APIKey, APIKeyContext


class APIKeyService:
    """Service for API key management and validation"""
    
    # Rate limiting: track requests per key per minute
    _rate_limit_cache: dict = {}  # {key_id: {count: int, reset_at: float}}
    
    # Tier configurations
    TIER_CONFIGS = {
        'free': {
            'searches_per_month': 10,
            'rate_limit_per_minute': 5
        },
        'basic': {
            'searches_per_month': 50,
            'rate_limit_per_minute': 10
        },
        'pro': {
            'searches_per_month': 200,
            'rate_limit_per_minute': 20
        },
        'enterprise': {
            'searches_per_month': -1,  # Unlimited
            'rate_limit_per_minute': 50
        }
    }
    
    @staticmethod
    def generate_api_key() -> tuple[str, str]:
        """
        Generate a new API key.
        
        Returns:
            (full_key, key_prefix) - Full key should be shown once, prefix for identification
        """
        # Generate 32-byte random key, encode as hex (64 chars)
        full_key = secrets.token_urlsafe(32)
        key_prefix = full_key[:8]  # First 8 chars for identification
        return full_key, key_prefix
    
    @staticmethod
    def hash_api_key(key: str) -> str:
        """Hash an API key using bcrypt"""
        return bcrypt.hashpw(key.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    @staticmethod
    def verify_api_key(key: str, key_hash: str) -> bool:
        """Verify an API key against its hash"""
        try:
            return bcrypt.checkpw(key.encode('utf-8'), key_hash.encode('utf-8'))
        except Exception:
            return False
    
    @classmethod
    def validate_api_key(cls, key: str) -> Optional[APIKeyContext]:
        """
        Validate an API key and return context.
        
        Args:
            key: The API key to validate
            
        Returns:
            APIKeyContext if valid, None if invalid
        """
        if not key:
            return None
        
        # Extract prefix (first 8 chars) for lookup
        key_prefix = key[:8]
        
        client = get_client()
        
        try:
            # Find key by prefix
            result = client.table('api_keys').select('*').eq('key_prefix', key_prefix).eq('is_active', True).execute()
            
            if not result.data:
                return None
            
            # Multiple keys could have same prefix (unlikely), check all
            for key_record in result.data:
                key_hash = key_record['key_hash']
                
                # Verify the actual key matches
                if cls.verify_api_key(key, key_hash):
                    api_key = APIKey(**key_record)
                    
                    # Check if expired
                    if api_key.expires_at and datetime.utcnow() > api_key.expires_at.replace(tzinfo=None):
                        return None
                    
                    # Calculate remaining searches
                    searches_remaining = api_key.searches_per_month - api_key.searches_used_this_month
                    if api_key.searches_per_month > 0:  # -1 means unlimited
                        searches_remaining = max(0, searches_remaining)
                    else:
                        searches_remaining = -1  # Unlimited
                    
                    return APIKeyContext(
                        key_id=api_key.id,
                        user_id=api_key.user_id,
                        tier=api_key.tier,
                        searches_per_month=api_key.searches_per_month,
                        searches_used_this_month=api_key.searches_used_this_month,
                        searches_remaining=searches_remaining,
                        rate_limit_per_minute=api_key.rate_limit_per_minute,
                        is_active=api_key.is_active
                    )
            
            return None
            
        except Exception as e:
            print(f"Error validating API key: {e}")
            return None
    
    @classmethod
    def check_rate_limit(cls, key_id: UUID) -> tuple[bool, Optional[dict]]:
        """
        Check if API key is within rate limit.
        
        Args:
            key_id: The API key ID
            
        Returns:
            (is_allowed, error_details) - error_details if not allowed
        """
        now = time.time()
        
        # Get key record to check tier limits
        client = get_client()
        try:
            result = client.table('api_keys').select('rate_limit_per_minute').eq('id', str(key_id)).execute()
            if not result.data:
                return False, {'message': 'API key not found'}
            
            rate_limit = result.data[0]['rate_limit_per_minute']
        except Exception as e:
            return False, {'message': f'Database error: {str(e)}'}
        
        # Check in-memory cache
        if key_id in cls._rate_limit_cache:
            cache_entry = cls._rate_limit_cache[key_id]
            
            # Reset if minute has passed
            if now >= cache_entry['reset_at']:
                cache_entry['count'] = 0
                cache_entry['reset_at'] = now + 60  # Reset in 60 seconds
            
            # Check if limit exceeded
            if cache_entry['count'] >= rate_limit:
                reset_in = int(cache_entry['reset_at'] - now)
                return False, {
                    'message': f'Rate limit exceeded. Try again in {reset_in} seconds.',
                    'reset_in_seconds': reset_in,
                    'limit': rate_limit
                }
            
            # Increment counter
            cache_entry['count'] += 1
        else:
            # Initialize cache entry
            cls._rate_limit_cache[key_id] = {
                'count': 1,
                'reset_at': now + 60
            }
        
        return True, None
    
    @classmethod
    def check_quota(cls, key_id: UUID) -> tuple[bool, Optional[dict]]:
        """
        Check if API key has remaining quota.
        
        Args:
            key_id: The API key ID
            
        Returns:
            (has_quota, error_details) - error_details if no quota
        """
        client = get_client()
        
        try:
            result = client.table('api_keys').select('searches_per_month, searches_used_this_month').eq('id', str(key_id)).execute()
            
            if not result.data:
                return False, {'message': 'API key not found'}
            
            searches_per_month = result.data[0]['searches_per_month']
            searches_used = result.data[0]['searches_used_this_month']
            
            # -1 means unlimited
            if searches_per_month == -1:
                return True, None
            
            if searches_used >= searches_per_month:
                return False, {
                    'message': f'Monthly quota exceeded. {searches_used}/{searches_per_month} searches used.',
                    'searches_used': searches_used,
                    'searches_per_month': searches_per_month
                }
            
            return True, None
            
        except Exception as e:
            return False, {'message': f'Database error: {str(e)}'}
    
    @classmethod
    def increment_usage(cls, key_id: UUID):
        """Increment search usage for an API key"""
        client = get_client()
        
        try:
            # Increment searches_used_this_month and update last_used_at
            client.table('api_keys').update({
                'searches_used_this_month': client.rpc('increment', {'key': 'searches_used_this_month'}),
                'last_used_at': datetime.utcnow().isoformat()
            }).eq('id', str(key_id)).execute()
            
            # Alternative: use SQL increment
            # For Supabase, we need to use RPC or select + update
            result = client.table('api_keys').select('searches_used_this_month').eq('id', str(key_id)).execute()
            if result.data:
                current = result.data[0]['searches_used_this_month']
                client.table('api_keys').update({
                    'searches_used_this_month': current + 1,
                    'last_used_at': datetime.utcnow().isoformat()
                }).eq('id', str(key_id)).execute()
                
        except Exception as e:
            print(f"Error incrementing API key usage: {e}")
    
    @classmethod
    def get_remaining_quota(cls, key_id: UUID) -> dict:
        """Get remaining quota information for an API key"""
        client = get_client()
        
        try:
            result = client.table('api_keys').select(
                'searches_per_month, searches_used_this_month, tier, rate_limit_per_minute'
            ).eq('id', str(key_id)).execute()
            
            if not result.data:
                return {'error': 'API key not found'}
            
            data = result.data[0]
            searches_per_month = data['searches_per_month']
            searches_used = data['searches_used_this_month']
            
            if searches_per_month == -1:
                searches_remaining = -1  # Unlimited
            else:
                searches_remaining = max(0, searches_per_month - searches_used)
            
            return {
                'tier': data['tier'],
                'searches_per_month': searches_per_month,
                'searches_used_this_month': searches_used,
                'searches_remaining': searches_remaining,
                'rate_limit_per_minute': data['rate_limit_per_minute']
            }
            
        except Exception as e:
            return {'error': f'Database error: {str(e)}'}


def create_api_key_for_user(user_id: UUID, tier: str = 'free') -> tuple[str, dict]:
    """
    Create a new API key for a user.
    
    Args:
        user_id: User UUID from profiles table
        tier: Subscription tier (free, basic, pro, enterprise)
        
    Returns:
        (full_key, key_record) - Full key to return to user (show once!), key metadata
    """
    service = APIKeyService()
    full_key, key_prefix = service.generate_api_key()
    key_hash = service.hash_api_key(full_key)
    
    tier_config = service.TIER_CONFIGS.get(tier, service.TIER_CONFIGS['free'])
    
    key_data = {
        'user_id': str(user_id),
        'key_hash': key_hash,
        'key_prefix': key_prefix,
        'tier': tier,
        'searches_per_month': tier_config['searches_per_month'],
        'rate_limit_per_minute': tier_config['rate_limit_per_minute'],
        'is_active': True
    }
    
    client = get_client()
    result = client.table('api_keys').insert(key_data).execute()
    
    if result.data:
        return full_key, result.data[0]
    
    raise Exception("Failed to create API key")

