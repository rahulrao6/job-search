"""User authentication and rate limiting service using Supabase Auth"""

import time
from typing import Optional, Tuple
from uuid import UUID
from supabase import Client
from src.db.supabase_client import get_client


class UserContext:
    """Context for authenticated user"""
    def __init__(self, user_id: UUID, tier: str, searches_per_month: int, 
                 searches_used_this_month: int, rate_limit_per_minute: int):
        self.user_id = user_id
        self.tier = tier
        self.searches_per_month = searches_per_month
        self.searches_used_this_month = searches_used_this_month
        self.rate_limit_per_minute = rate_limit_per_minute
        self.searches_remaining = searches_per_month - searches_used_this_month if searches_per_month > 0 else -1


class UserService:
    """Service for user authentication and rate limiting"""
    
    # Rate limiting cache: {user_id: {count: int, reset_at: float}}
    _rate_limit_cache: dict = {}
    
    # Subscription tier configurations
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
    
    @classmethod
    def validate_user_token(cls, token: str) -> Optional[UserContext]:
        """
        Validate Supabase JWT token and return user context.
        
        Args:
            token: JWT token from Supabase Auth
            
        Returns:
            UserContext if valid, None if invalid
        """
        if not token:
            return None
        
        client = get_client()
        
        try:
            # Verify token using Supabase Auth
            # The get_user method validates the token and returns user info
            response = client.auth.get_user(token)
            
            if not response or not response.user:
                return None
            
            user_id = UUID(response.user.id)
            
            # Get user profile and subscription tier
            profile_result = client.table('profiles').select('id, subscription_tier, searches_used_this_month').eq('id', str(user_id)).execute()
            
            if not profile_result.data:
                # Actually create default profile entry in database if missing
                try:
                    # Get user email from auth response
                    user_email = response.user.email or ''
                    client.table('profiles').insert({
                        'id': str(user_id),
                        'email': user_email,
                        'subscription_tier': 'free',
                        'searches_used_this_month': 0
                    }).execute()
                    tier = 'free'
                    searches_used = 0
                except Exception as e:
                    # If insert fails (e.g., profile exists but query failed), try to get it again
                    print(f"Warning: Could not create profile, trying to fetch again: {e}")
                    profile_result = client.table('profiles').select('id, subscription_tier, searches_used_this_month').eq('id', str(user_id)).execute()
                    if profile_result.data:
                        profile = profile_result.data[0]
                        tier = profile.get('subscription_tier') or 'free'
                        searches_used = profile.get('searches_used_this_month')
                        if searches_used is None:
                            searches_used = 0
                    else:
                        # Fallback to defaults if still can't get profile
                        tier = 'free'
                        searches_used = 0
            else:
                profile = profile_result.data[0]
                tier = profile.get('subscription_tier', 'free') or 'free'
                searches_used = profile.get('searches_used_this_month')
                if searches_used is None:
                    searches_used = 0
            
            tier_config = cls.TIER_CONFIGS.get(tier, cls.TIER_CONFIGS['free'])
            
            return UserContext(
                user_id=user_id,
                tier=tier,
                searches_per_month=tier_config['searches_per_month'],
                searches_used_this_month=searches_used,
                rate_limit_per_minute=tier_config['rate_limit_per_minute']
            )
            
        except Exception as e:
            print(f"Error validating user token: {e}")
            return None
    
    @classmethod
    def check_rate_limit(cls, user_id: UUID) -> Tuple[bool, Optional[dict]]:
        """
        Check if user is within rate limit (does NOT increment counter).
        Call increment_rate_limit() after successful request.
        
        Args:
            user_id: User UUID
            
        Returns:
            (is_allowed, error_details) - error_details if not allowed
        """
        now = time.time()
        
        # Get user tier for rate limit
        client = get_client()
        try:
            result = client.table('profiles').select('subscription_tier').eq('id', str(user_id)).execute()
            if not result.data:
                # If profile doesn't exist, create it with defaults
                try:
                    client.table('profiles').insert({
                        'id': str(user_id),
                        'subscription_tier': 'free'
                    }).execute()
                    tier = 'free'
                except Exception as e:
                    print(f"Error creating profile in check_rate_limit: {e}")
                    return False, {'message': 'User profile not found and could not be created'}
            else:
                tier = result.data[0].get('subscription_tier') or 'free'
            
            rate_limit = cls.TIER_CONFIGS.get(tier, cls.TIER_CONFIGS['free'])['rate_limit_per_minute']
        except Exception as e:
            print(f"Error in check_rate_limit: {e}")
            return False, {'message': f'Database error: {str(e)}'}
        
        # Check in-memory cache
        if user_id in cls._rate_limit_cache:
            cache_entry = cls._rate_limit_cache[user_id]
            
            # Reset if minute has passed
            if now >= cache_entry['reset_at']:
                cache_entry['count'] = 0
                cache_entry['reset_at'] = now + 60
            
            # Check if limit exceeded (before incrementing)
            if cache_entry['count'] >= rate_limit:
                reset_in = int(cache_entry['reset_at'] - now)
                return False, {
                    'message': f'Rate limit exceeded. Try again in {reset_in} seconds.',
                    'reset_in_seconds': reset_in,
                    'limit': rate_limit
                }
        else:
            # Initialize cache entry (but don't count yet)
            cls._rate_limit_cache[user_id] = {
                'count': 0,
                'reset_at': now + 60
            }
        
        return True, None
    
    @classmethod
    def increment_rate_limit(cls, user_id: UUID):
        """
        Increment rate limit counter for a successful request.
        Should only be called after check_rate_limit() passes and request succeeds.
        
        Args:
            user_id: User UUID
        """
        now = time.time()
        
        if user_id in cls._rate_limit_cache:
            cache_entry = cls._rate_limit_cache[user_id]
            
            # Reset if minute has passed
            if now >= cache_entry['reset_at']:
                cache_entry['count'] = 0
                cache_entry['reset_at'] = now + 60
            
            # Increment counter
            cache_entry['count'] += 1
        else:
            # Initialize cache entry
            cls._rate_limit_cache[user_id] = {
                'count': 1,
                'reset_at': now + 60
            }
    
    @classmethod
    def check_quota(cls, user_id: UUID) -> Tuple[bool, Optional[dict]]:
        """
        Check if user has remaining quota.
        
        Args:
            user_id: User UUID
            
        Returns:
            (has_quota, error_details) - error_details if no quota
        """
        client = get_client()
        
        try:
            result = client.table('profiles').select('subscription_tier, searches_used_this_month').eq('id', str(user_id)).execute()
            
            if not result.data:
                # If profile doesn't exist, create it with defaults
                try:
                    client.table('profiles').insert({
                        'id': str(user_id),
                        'subscription_tier': 'free',
                        'searches_used_this_month': 0
                    }).execute()
                    tier = 'free'
                    searches_used = 0
                except Exception as e:
                    # If insert fails, return error
                    print(f"Error creating profile in check_quota: {e}")
                    return False, {'message': 'User profile not found and could not be created'}
            else:
                tier = result.data[0].get('subscription_tier') or 'free'
                searches_used = result.data[0].get('searches_used_this_month')
                if searches_used is None:
                    searches_used = 0
            
            tier_config = cls.TIER_CONFIGS.get(tier, cls.TIER_CONFIGS['free'])
            searches_per_month = tier_config['searches_per_month']
            
            # -1 means unlimited
            if searches_per_month == -1:
                return True, None
            
            # Ensure searches_per_month is valid (should be > 0)
            if searches_per_month <= 0:
                return False, {
                    'message': 'Invalid quota configuration. Please contact support.',
                    'searches_used': searches_used,
                    'searches_per_month': searches_per_month
                }
            
            if searches_used >= searches_per_month:
                return False, {
                    'message': f'Monthly quota exceeded. {searches_used}/{searches_per_month} searches used.',
                    'searches_used': searches_used,
                    'searches_per_month': searches_per_month
                }
            
            return True, None
            
        except Exception as e:
            print(f"Error in check_quota: {e}")
            import traceback
            traceback.print_exc()
            return False, {'message': f'Database error: {str(e)}'}
    
    @classmethod
    def increment_usage(cls, user_id: UUID):
        """Increment search usage for a user"""
        client = get_client()
        
        try:
            # Get current count
            result = client.table('profiles').select('searches_used_this_month').eq('id', str(user_id)).execute()
            if result.data:
                current = result.data[0].get('searches_used_this_month')
                if current is None:
                    current = 0
                client.table('profiles').update({
                    'searches_used_this_month': current + 1
                }).eq('id', str(user_id)).execute()
            else:
                # Create profile if it doesn't exist
                client.table('profiles').insert({
                    'id': str(user_id),
                    'searches_used_this_month': 1
                }).execute()
        except Exception as e:
            print(f"Error incrementing user usage: {e}")
    
    @classmethod
    def get_user_quota(cls, user_id: UUID) -> dict:
        """Get remaining quota information for a user"""
        client = get_client()
        
        try:
            result = client.table('profiles').select('subscription_tier, searches_used_this_month').eq('id', str(user_id)).execute()
            
            if not result.data:
                return {'error': 'User profile not found'}
            
            tier = result.data[0].get('subscription_tier') or 'free'
            searches_used = result.data[0].get('searches_used_this_month')
            if searches_used is None:
                searches_used = 0
            
            tier_config = cls.TIER_CONFIGS.get(tier, cls.TIER_CONFIGS['free'])
            searches_per_month = tier_config['searches_per_month']
            
            if searches_per_month == -1:
                searches_remaining = -1  # Unlimited
            else:
                searches_remaining = max(0, searches_per_month - searches_used)
            
            return {
                'tier': tier,
                'searches_per_month': searches_per_month,
                'searches_used_this_month': searches_used,
                'searches_remaining': searches_remaining,
                'rate_limit_per_minute': tier_config['rate_limit_per_minute']
            }
            
        except Exception as e:
            return {'error': f'Database error: {str(e)}'}
    
    @classmethod
    def update_subscription_tier(cls, user_id: UUID, tier: str):
        """Update user's subscription tier"""
        if tier not in cls.TIER_CONFIGS:
            raise ValueError(f"Invalid tier: {tier}")
        
        client = get_client()
        
        try:
            client.table('profiles').update({
                'subscription_tier': tier
            }).eq('id', str(user_id)).execute()
        except Exception as e:
            print(f"Error updating subscription tier: {e}")
            raise

