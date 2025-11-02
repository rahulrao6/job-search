"""Middleware for error handling, CORS, and request processing"""

from functools import wraps
from flask import jsonify, request
from typing import Callable
import traceback


class APIError(Exception):
    """Base API exception"""
    def __init__(self, code: str, message: str, status_code: int = 400, details: dict = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class APIKeyNotFound(APIError):
    """API key not found"""
    def __init__(self, message: str = "API key not found"):
        super().__init__('API_KEY_NOT_FOUND', message, 401)


class RateLimitExceeded(APIError):
    """Rate limit exceeded"""
    def __init__(self, message: str = "Rate limit exceeded", details: dict = None):
        super().__init__('RATE_LIMIT_EXCEEDED', message, 429, details)


class QuotaExceeded(APIError):
    """Quota exceeded"""
    def __init__(self, message: str = "Monthly quota exceeded", details: dict = None):
        super().__init__('QUOTA_EXCEEDED', message, 429, details)


class InvalidRequest(APIError):
    """Invalid request"""
    def __init__(self, message: str = "Invalid request", details: dict = None):
        super().__init__('INVALID_REQUEST', message, 400, details)


class DatabaseError(APIError):
    """Database error"""
    def __init__(self, message: str = "Database error", details: dict = None):
        super().__init__('DATABASE_ERROR', message, 500, details)


def handle_api_errors(app):
    """Register error handlers for Flask app"""
    
    @app.errorhandler(APIError)
    def handle_api_error(error: APIError):
        """Handle custom API errors"""
        return jsonify({
            'success': False,
            'error': {
                'code': error.code,
                'message': error.message,
                'details': error.details
            }
        }), error.status_code
    
    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle 404 errors"""
        return jsonify({
            'success': False,
            'error': {
                'code': 'NOT_FOUND',
                'message': 'Endpoint not found',
                'details': {'path': request.path}
            }
        }), 404
    
    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        """Handle 405 errors"""
        return jsonify({
            'success': False,
            'error': {
                'code': 'METHOD_NOT_ALLOWED',
                'message': 'HTTP method not allowed for this endpoint',
                'details': {'method': request.method, 'path': request.path}
            }
        }), 405
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        """Handle 500 errors"""
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_SERVER_ERROR',
                'message': 'An internal server error occurred',
                'details': {}
            }
        }), 500


def handle_exceptions(f):
    """
    Decorator to catch and handle exceptions in route handlers.
    Converts exceptions to standardized error responses.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except APIError as e:
            # Re-raise API errors (they'll be handled by error handler)
            raise
        except ValueError as e:
            raise InvalidRequest(str(e))
        except KeyError as e:
            raise InvalidRequest(f"Missing required field: {str(e)}")
        except Exception as e:
            # Log the full traceback for debugging
            print(f"Unhandled exception in {f.__name__}: {e}")
            traceback.print_exc()
            raise APIError(
                'INTERNAL_SERVER_ERROR',
                'An unexpected error occurred',
                500,
                {'exception_type': type(e).__name__}
            )
    
    return decorated_function

