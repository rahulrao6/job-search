"""Structured logging configuration for production"""

import json
import logging
import sys
from datetime import datetime
from typing import Optional, Dict, Any
import os
from functools import wraps
from flask import request, g


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data: Dict[str, Any] = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add request ID if available (only if Flask g is available)
        try:
            from flask import g
            if hasattr(g, 'request_id'):
                log_data['request_id'] = g.request_id
            
            # Add user ID if available
            if hasattr(g, 'user_id'):
                log_data['user_id'] = str(g.user_id)
        except (ImportError, RuntimeError):
            # Flask context not available (e.g., called outside request context)
            pass
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                          'levelname', 'levelno', 'lineno', 'module', 'msecs',
                          'message', 'pathname', 'process', 'processName', 'relativeCreated',
                          'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info']:
                log_data[key] = value
        
        return json.dumps(log_data)


class StructuredFormatter(logging.Formatter):
    """Human-readable structured formatter for development"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as readable string"""
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        parts = [
            f"[{timestamp}]",
            f"{record.levelname:8s}",
            f"{record.module}:{record.lineno}",
        ]
        
        # Add request ID if available (only if Flask g is available)
        try:
            from flask import g
            if hasattr(g, 'request_id'):
                parts.append(f"[req:{g.request_id[:8]}]")
            
            # Add user ID if available
            if hasattr(g, 'user_id'):
                parts.append(f"[user:{str(g.user_id)[:8]}]")
        except (ImportError, RuntimeError):
            # Flask context not available (e.g., called outside request context)
            pass
        
        parts.append(f"- {record.getMessage()}")
        
        # Add exception info if present
        if record.exc_info:
            parts.append(f"\n{self.formatException(record.exc_info)}")
        
        return " ".join(parts)


def setup_logging(log_level: Optional[str] = None, use_json: Optional[bool] = None):
    """
    Setup application-wide logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_json: Whether to use JSON formatting. If None, auto-detect from environment
    """
    # Determine log level
    if log_level is None:
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    level = getattr(logging, log_level, logging.INFO)
    
    # Determine if JSON formatting should be used
    if use_json is None:
        use_json = os.getenv('LOG_FORMAT', 'json').lower() == 'json' or \
                   os.getenv('ENVIRONMENT', '').lower() == 'production'
    
    # Create formatter
    if use_json:
        formatter = JSONFormatter()
    else:
        formatter = StructuredFormatter()
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    
    # Set levels for noisy libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('supabase').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name"""
    return logging.getLogger(name)


def log_request(f):
    """Decorator to add request ID tracking and timing to Flask routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import g, request
        import uuid
        import time as time_module
        
        # Get logger for this module
        logger = get_logger(__name__)
        
        g.request_id = str(uuid.uuid4())
        g.request_start_time = time_module.time()
        
        # Add user ID from context if available
        if hasattr(request, 'user_context') and request.user_context:
            g.user_id = request.user_context.user_id
        
        try:
            response = f(*args, **kwargs)
            
            # Track request duration
            duration_ms = (time_module.time() - g.request_start_time) * 1000
            
            # Log slow requests (>5s) as warnings
            if duration_ms > 5000:
                logger.warning(f"Slow request: {request.path} took {duration_ms:.0f}ms")
            
            # Record metrics if available
            try:
                from src.utils.metrics import get_metrics_tracker
                metrics = get_metrics_tracker()
                # Extract status code from Flask response (can be tuple or Response object)
                if isinstance(response, tuple):
                    status_code = response[1] if len(response) > 1 else 200
                elif hasattr(response, 'status_code'):
                    status_code = response.status_code
                else:
                    status_code = 200
                
                metrics.record_request(
                    endpoint=request.path,
                    status_code=status_code,
                    duration_ms=duration_ms
                )
            except Exception:
                pass  # Don't fail if metrics tracking fails
            
            logger.debug(f"Request {request.path} completed in {duration_ms:.0f}ms")
            
            return response
            
        except Exception as e:
            # Track duration even on errors
            duration_ms = (time_module.time() - g.request_start_time) * 1000
            
            # Get logger (in case exception happened before logger was defined)
            logger = get_logger(__name__)
            
            # Record error metrics
            try:
                from src.utils.metrics import get_metrics_tracker
                metrics = get_metrics_tracker()
                metrics.record_request(
                    endpoint=request.path,
                    status_code=500,
                    duration_ms=duration_ms
                )
            except Exception:
                pass
            
            logger.error(f"Request {request.path} failed after {duration_ms:.0f}ms: {e}", exc_info=True)
            raise
    
    return decorated_function

