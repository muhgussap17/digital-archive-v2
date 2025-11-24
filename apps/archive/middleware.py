import logging
from django.utils.deprecation import MiddlewareMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404
from .utils import extract_client_ip

logger = logging.getLogger(__name__)


class AuditLogMiddleware(MiddlewareMixin):
    """
    Middleware to log all requests for audit trail
    """
    
    def process_request(self, request):
        """Log request details"""
        if request.user.is_authenticated:
            logger.info(
                f"Request: {request.method} {request.path} | "
                f"User: {request.user.username} | "
                f"IP: {extract_client_ip(request)}" # type: ignore
            )
        return None
    
    def process_exception(self, request, exception):
        """Log exceptions"""
        if isinstance(exception, (PermissionDenied, Http404)):
            # Don't log common exceptions
            return None
        
        logger.error(
            f"Exception: {type(exception).__name__} | "
            f"Path: {request.path} | "
            f"User: {request.user.username if request.user.is_authenticated else 'Anonymous'} | "
            f"Message: {str(exception)}"
        )
        return None


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Add security headers to responses
    """
    
    def process_response(self, request, response):
        """Add security headers"""
        # Prevent clickjacking
        response['X-Frame-Options'] = 'DENY'
        
        # Prevent MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'
        
        # XSS protection
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        return response