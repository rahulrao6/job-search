"""Authentication middleware for API routes using Supabase Auth"""

import os
from functools import wraps
from flask import request, jsonify
from typing import Optional
from src.services.user_service import UserService, UserContext


def get_token_from_request() -> Optional[str]:
    """Extract JWT token from request headers"""
    # Check Authorization header: Bearer <token>
    auth_header = request.headers.get('Authorization', '')
    
    if auth_header.startswith('Bearer '):
        return auth_header[7:].strip()
    
    return None


def require_auth(f):
    """
    Decorator to require user authentication via Supabase JWT.
    
    Usage:
        @require_auth
        def my_route():
            user_context = request.user_context
            # Use user_context.user_id, etc.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_token_from_request()
        
        if not token:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'AUTH_REQUIRED',
                    'message': 'Authentication required. Please sign in and provide your token in Authorization: Bearer <token> header.',
                    'details': {}
                }
            }), 401
        
        # Validate user token
        user_context = UserService.validate_user_token(token)
        
        if not user_context:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'AUTH_INVALID',
                    'message': 'Invalid or expired authentication token. Please sign in again.',
                    'details': {}
                }
            }), 401
        
        # Attach context to request for route handlers
        request.user_context = user_context
        
        # Check if rate limiting is disabled (for testing/development)
        rate_limit_disabled = os.getenv('DISABLE_RATE_LIMIT', 'false').lower() == 'true'
        
#        Check quota
        has_quota, quota_error = UserService.check_quota(user_context.user_id)
        if not has_quota:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'QUOTA_EXCEEDED',
                    'message': quota_error.get('message', 'Monthly quota exceeded'),
                    'details': quota_error
                }
            }), 429
        
        # Check rate limit (skip if disabled)
        if not rate_limit_disabled:
            is_allowed, rate_limit_error = UserService.check_rate_limit(user_context.user_id)
            if not is_allowed:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'RATE_LIMIT_EXCEEDED',
                        'message': rate_limit_error.get('message', 'Rate limit exceeded'),
                        'details': rate_limit_error
                    }
                }), 429
        
        # Mark that we've checked rate limit so we can increment it after successful request
        request._rate_limit_checked = True
        
        return f(*args, **kwargs)
    
    return decorated_function


def optional_auth(f):
    """
    Decorator for routes where authentication is optional.
    If provided, validates and attaches context.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_token_from_request()
        
        if token:
            user_context = UserService.validate_user_token(token)
            if user_context:
                request.user_context = user_context
            else:
                request.user_context = None
        else:
            request.user_context = None
        
        return f(*args, **kwargs)
    
    return decorated_function

