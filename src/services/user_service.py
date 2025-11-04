"""User authentication and rate limiting service using Supabase Auth"""

import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple
from uuid import UUID
from supabase import Client
from src.db.supabase_client import get_client

logger = logging.getLogger(__name__)


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
    
    # Keep a small local cache for hot paths (1-minute TTL)
    # This reduces database load but doesn't replace database-backed rate limiting
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
                    logger.warning(f"Could not create profile, trying to fetch again: {e}")
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
            logger.error(f"Error validating user token: {e}", exc_info=True)
            return None
    
    @classmethod
    def check_rate_limit(cls, user_id: UUID) -> Tuple[bool, Optional[dict]]:
        """
        Check if user is within rate limit using database-backed rate limiting.
        Does NOT increment counter. Call increment_rate_limit() after successful request.
        
        Args:
            user_id: User UUID
            
        Returns:
            (is_allowed, error_details) - error_details if not allowed
        """
        client = get_client()
        
        try:
            # Get user tier for rate limit
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
                    logger.error(f"Error creating profile in check_rate_limit: {e}", exc_info=True)
                    return False, {'message': 'User profile not found and could not be created'}
            else:
                tier = result.data[0].get('subscription_tier') or 'free'
            
            rate_limit = cls.TIER_CONFIGS.get(tier, cls.TIER_CONFIGS['free'])['rate_limit_per_minute']
            
            # Calculate current window (minute-based)
            now = datetime.utcnow()
            window_start = now.replace(second=0, microsecond=0)
            reset_at = window_start + timedelta(minutes=1)
            
            # Try to get or create rate limit record using database function
            # This ensures atomicity across all instances
            try:
                # Use RPC function for atomic get-or-create
                rpc_result = client.rpc(
                    'get_or_create_rate_limit',
                    {
                        'p_user_id': str(user_id),
                        'p_window_start': window_start.isoformat(),
                        'p_reset_at': reset_at.isoformat()
                    }
                ).execute()
                
                if rpc_result.data and len(rpc_result.data) > 0:
                    request_count = rpc_result.data[0].get('request_count', 0)
                    
                    # Check if limit exceeded
                    if request_count >= rate_limit:
                        reset_in_seconds = int((reset_at - now).total_seconds())
                        return False, {
                            'message': f'Rate limit exceeded. Try again in {reset_in_seconds} seconds.',
                            'reset_in_seconds': max(1, reset_in_seconds),
                            'limit': rate_limit
                        }
            except Exception as rpc_error:
                # If RPC function doesn't exist, fall back to manual query/insert
                logger.warning(f"RPC function not available, using fallback method: {rpc_error}")
                
                # Try to get existing record
                existing = client.table('rate_limits').select('request_count').eq('user_id', str(user_id)).eq('window_start', window_start.isoformat()).execute()
                
                if existing.data and len(existing.data) > 0:
                    request_count = existing.data[0].get('request_count', 0)
                    
                    if request_count >= rate_limit:
                        reset_in_seconds = int((reset_at - now).total_seconds())
                        return False, {
                            'message': f'Rate limit exceeded. Try again in {reset_in_seconds} seconds.',
                            'reset_in_seconds': max(1, reset_in_seconds),
                            'limit': rate_limit
                        }
                else:
                    # Create new record (will be used by increment)
                    # Don't count this as a request yet
                    pass
            
            # Also check local cache for hot path optimization
            now_ts = time.time()
            if user_id in cls._rate_limit_cache:
                cache_entry = cls._rate_limit_cache[user_id]
                if now_ts >= cache_entry['reset_at']:
                    # Cache expired, remove it
                    del cls._rate_limit_cache[user_id]
                elif cache_entry['count'] >= rate_limit:
                    # Local cache shows limit exceeded (defensive check)
                    reset_in = int(cache_entry['reset_at'] - now_ts)
                    return False, {
                        'message': f'Rate limit exceeded. Try again in {reset_in} seconds.',
                        'reset_in_seconds': max(1, reset_in),
                        'limit': rate_limit
                    }
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error in check_rate_limit: {e}", exc_info=True)
            return False, {'message': f'Database error: {str(e)}'}
    
    @classmethod
    def increment_rate_limit(cls, user_id: UUID):
        """
        Increment rate limit counter for a successful request using database.
        Should only be called after check_rate_limit() passes and request succeeds.
        
        Args:
            user_id: User UUID
        """
        client = get_client()
        
        try:
            # Calculate current window (minute-based)
            now = datetime.utcnow()
            window_start = now.replace(second=0, microsecond=0)
            reset_at = window_start + timedelta(minutes=1)
            
            # Try to use RPC function for atomic increment
            try:
                new_count = client.rpc(
                    'increment_rate_limit',
                    {
                        'p_user_id': str(user_id),
                        'p_window_start': window_start.isoformat()
                    }
                ).execute()
                
                # If RPC fails (record doesn't exist), create it
                if not new_count.data or (isinstance(new_count.data, int) and new_count.data == 0):
                    # Create record if it doesn't exist
                    client.table('rate_limits').upsert({
                        'user_id': str(user_id),
                        'window_start': window_start.isoformat(),
                        'request_count': 1,
                        'reset_at': reset_at.isoformat()
                    }).execute()
            except Exception as rpc_error:
                # Fallback to manual upsert if RPC doesn't exist
                logger.warning(f"RPC function not available, using fallback method: {rpc_error}")
                
                # Get existing or create new
                existing = client.table('rate_limits').select('request_count').eq('user_id', str(user_id)).eq('window_start', window_start.isoformat()).execute()
                
                if existing.data and len(existing.data) > 0:
                    current_count = existing.data[0].get('request_count', 0)
                    client.table('rate_limits').update({
                        'request_count': current_count + 1,
                        'updated_at': now.isoformat()
                    }).eq('user_id', str(user_id)).eq('window_start', window_start.isoformat()).execute()
                else:
                    client.table('rate_limits').insert({
                        'user_id': str(user_id),
                        'window_start': window_start.isoformat(),
                        'request_count': 1,
                        'reset_at': reset_at.isoformat()
                    }).execute()
            
            # Update local cache for hot path
            now_ts = time.time()
            if user_id in cls._rate_limit_cache:
                cache_entry = cls._rate_limit_cache[user_id]
                if now_ts < cache_entry['reset_at']:
                    cache_entry['count'] += 1
                else:
                    # Reset cache for new window
                    cls._rate_limit_cache[user_id] = {
                        'count': 1,
                        'reset_at': now_ts + 60
                    }
            else:
                cls._rate_limit_cache[user_id] = {
                    'count': 1,
                    'reset_at': now_ts + 60
                }
            
        except Exception as e:
            logger.error(f"Error incrementing rate limit: {e}", exc_info=True)
            # Don't fail the request if rate limit increment fails
    
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
                    logger.error(f"Error creating profile in check_quota: {e}", exc_info=True)
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
            logger.error(f"Error in check_quota: {e}", exc_info=True)
            return False, {'message': f'Database error: {str(e)}'}
    
    @classmethod
    def increment_usage(cls, user_id: UUID):
        """Increment search usage for a user. Skip for enterprise unlimited users."""
        client = get_client()
        
        try:
            # Check if user has unlimited quota (enterprise tier)
            result = client.table('profiles').select('subscription_tier, searches_used_this_month').eq('id', str(user_id)).execute()
            
            if result.data:
                tier = result.data[0].get('subscription_tier') or 'free'
                tier_config = cls.TIER_CONFIGS.get(tier, cls.TIER_CONFIGS['free'])
                
                # Skip increment for enterprise unlimited users
                if tier_config['searches_per_month'] == -1:
                    logger.debug(f"Skipping usage increment for enterprise user {user_id} (unlimited quota)")
                    return
                
                current = result.data[0].get('searches_used_this_month')
                if current is None:
                    current = 0
                client.table('profiles').update({
                    'searches_used_this_month': current + 1
                }).eq('id', str(user_id)).execute()
                
                logger.debug(f"Incremented usage for user {user_id}: {current + 1}")
            else:
                # Create profile if it doesn't exist
                client.table('profiles').insert({
                    'id': str(user_id),
                    'searches_used_this_month': 1,
                    'subscription_tier': 'free'
                }).execute()
                logger.debug(f"Created profile and incremented usage for user {user_id}")
        except Exception as e:
            logger.error(f"Error incrementing user usage: {e}", exc_info=True)
    
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
                # Enterprise unlimited: show large number instead of -1
                searches_remaining = 999999
                unlimited = True
            else:
                searches_remaining = max(0, searches_per_month - searches_used)
                unlimited = False
            
            return {
                'tier': tier,
                'searches_per_month': searches_per_month,
                'searches_used_this_month': searches_used,
                'searches_remaining': searches_remaining,
                'unlimited': unlimited,
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
            logger.error(f"Error updating subscription tier: {e}", exc_info=True)
            raise

