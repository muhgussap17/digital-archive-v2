"""
Modul: services/ajax_handler.py
Fungsi: Handler untuk AJAX responses dengan format konsisten

Berisi utilities untuk:
    - Build JSON responses untuk AJAX requests
    - Render form HTML fragments
    - Standardize success/error responses
    - Handle redirect URLs

Implementasi Standar:
    - Consistent response format untuk semua AJAX calls
    - Automatic AJAX detection
    - Type hints untuk better IDE support
    - Reusable across all views

Catatan Pemeliharaan:
    - Semua AJAX responses harus menggunakan class ini
    - Jangan hardcode response format di views
    - Update response schema di sini jika ada perubahan UI
    
Cara Penggunaan:
    from ..services import AjaxHandler
    
    # Success with redirect
    return AjaxHandler.success_redirect(
        message='Berhasil!',
        url='archive:document_list'
    )
    
    # Error response
    return AjaxHandler.error(
        message='Gagal!',
        errors=form.errors
    )
    
    # Form response (GET or invalid POST)
    return AjaxHandler.form_response(
        form=form,
        template='path/to/template.html',
        context={'is_update': False}
    )
"""

from typing import Optional, Dict, Any
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.contrib import messages


class AjaxHandler:
    """
    Handler untuk AJAX requests dengan response format konsisten
    
    Menyediakan static methods untuk build berbagai tipe response:
        - success_redirect: Success dengan redirect
        - success_data: Success dengan data JSON
        - error: Error response
        - form_response: Form HTML response (GET atau validation error)
    
    Response Format:
        Success: {
            'success': True,
            'message': str,
            'redirect_url': str (optional),
            'data': dict (optional)
        }
        
        Error: {
            'success': False,
            'message': str,
            'errors': dict (optional)
        }
        
        Form: {
            'success': True/False,
            'html': str,
            'errors': dict (optional)
        }
    """
    
    @staticmethod
    def is_ajax(request) -> bool:
        """
        Detect apakah request adalah AJAX
        
        Args:
            request: Django HttpRequest object
            
        Returns:
            bool: True jika AJAX request
            
        Examples:
            >>> if AjaxHandler.is_ajax(request):
            >>>     return AjaxHandler.success_redirect(...)
        """
        return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
    
    @staticmethod
    def success_redirect(
        message: str,
        url: str,
        request=None,
        status_code: int = 200
    ) -> JsonResponse:
        """
        Build success response dengan redirect
        
        Digunakan setelah operasi berhasil (create, update, delete)
        dan user perlu diarahkan ke halaman lain.
        
        Args:
            message: Success message untuk user
            url: URL name untuk redirect (e.g., 'archive:document_list')
            request: HttpRequest object (optional, untuk messages framework)
            status_code: HTTP status code (default: 200)
            
        Returns:
            JsonResponse: Success response dengan redirect_url
            
        Examples:
            >>> return AjaxHandler.success_redirect(
            ...     message='Dokumen berhasil diupload!',
            ...     url='archive:document_list',
            ...     request=request
            ... )
        
        Response Format:
            {
                'success': True,
                'message': 'Dokumen berhasil diupload!',
                'redirect_url': '/documents/'
            }
        """
        # Add message to Django messages framework jika request provided
        if request:
            messages.success(request, message)
        
        # Build absolute URL
        redirect_url = reverse(url) if ':' in url else url
        
        return JsonResponse({
            'success': True,
            'message': message,
            'redirect_url': redirect_url
        }, status=status_code)
    
    @staticmethod
    def success_data(
        message: str,
        data: Optional[Dict[str, Any]] = None,
        request=None,
        status_code: int = 200
    ) -> JsonResponse:
        """
        Build success response dengan data JSON
        
        Digunakan ketika perlu return data ke client tanpa redirect.
        Useful untuk AJAX calls yang update UI tanpa page reload.
        
        Args:
            message: Success message
            data: Additional data untuk return (optional)
            request: HttpRequest object (optional)
            status_code: HTTP status code (default: 200)
            
        Returns:
            JsonResponse: Success response dengan data
            
        Examples:
            >>> return AjaxHandler.success_data(
            ...     message='Data loaded',
            ...     data={'total': 100, 'items': [...]}
            ... )
        
        Response Format:
            {
                'success': True,
                'message': 'Data loaded',
                'data': {'total': 100, 'items': [...]}
            }
        """
        if request:
            messages.success(request, message)
        
        response = {
            'success': True,
            'message': message
        }
        
        if data:
            response['data'] = data
        
        return JsonResponse(response, status=status_code)
    
    @staticmethod
    def error(
        message: str,
        errors: Optional[Dict[str, Any]] = None,
        request=None,
        status_code: int = 400
    ) -> JsonResponse:
        """
        Build error response
        
        Digunakan ketika operasi gagal atau validation error.
        Akan include form errors jika provided.
        
        Args:
            message: Error message untuk user
            errors: Form errors atau validation errors (optional)
            request: HttpRequest object (optional)
            status_code: HTTP status code (default: 400 Bad Request)
            
        Returns:
            JsonResponse: Error response
            
        Examples:
            >>> return AjaxHandler.error(
            ...     message='Validasi gagal!',
            ...     errors=form.errors,
            ...     request=request
            ... )
        
        Response Format:
            {
                'success': False,
                'message': 'Validasi gagal!',
                'errors': {'field': ['Error message']}
            }
        """
        if request:
            messages.error(request, message)
        
        response = {
            'success': False,
            'message': message
        }
        
        if errors:
            response['errors'] = errors
        
        return JsonResponse(response, status=status_code)
    
    @staticmethod
    def form_response(
        form,
        template: str,
        context: Optional[Dict[str, Any]] = None,
        request=None,
        is_valid: bool = True
    ) -> JsonResponse:
        """
        Build form HTML response
        
        Digunakan untuk:
            - GET request: Return empty form
            - POST invalid: Return form dengan errors
        
        Args:
            form: Django Form instance
            template: Template path untuk render form HTML
            context: Additional context untuk template (optional)
            request: HttpRequest object (optional)
            is_valid: Form validation status (default: True)
            
        Returns:
            JsonResponse: Response dengan rendered HTML
            
        Examples:
            >>> # GET request
            >>> return AjaxHandler.form_response(
            ...     form=DocumentForm(),
            ...     template='archive/forms/document_form_content.html',
            ...     context={'is_update': False},
            ...     request=request
            ... )
            
            >>> # POST invalid
            >>> return AjaxHandler.form_response(
            ...     form=form,  # Form with errors
            ...     template='archive/forms/document_form_content.html',
            ...     context={'is_update': False},
            ...     request=request,
            ...     is_valid=False
            ... )
        
        Response Format:
            {
                'success': True/False,
                'html': '<div>...</div>',
                'errors': {...}  (jika is_valid=False)
            }
        """
        # Build context
        template_context = {'form': form}
        if context:
            template_context.update(context)
        
        # Render form HTML
        html = render_to_string(template, template_context, request=request)
        
        # Build response
        response = {
            'success': is_valid,
            'html': html
        }
        
        # Add errors jika form invalid
        if not is_valid and hasattr(form, 'errors'):
            response['errors'] = form.errors
        
        return JsonResponse(response)
    
    @staticmethod
    def detail_response(
        data: Dict[str, Any],
        status_code: int = 200
    ) -> JsonResponse:
        """
        Build detail response untuk AJAX detail views
        
        Digunakan untuk load document detail, activities, dll
        via AJAX untuk right panel atau modals.
        
        Args:
            data: Data dictionary untuk return
            status_code: HTTP status code (default: 200)
            
        Returns:
            JsonResponse: Response dengan data
            
        Examples:
            >>> return AjaxHandler.detail_response({
            ...     'success': True,
            ...     'document_name': 'ATK 2024-01-15',
            ...     'detail_html': '<div>...</div>'
            ... })
        """
        return JsonResponse(data, status=status_code)
    
    @staticmethod
    def handle_ajax_or_redirect(
        request,
        success: bool,
        message: str,
        redirect_url: str,
        errors: Optional[Dict[str, Any]] = None
    ):
        """
        Smart handler: AJAX response atau redirect based on request type
        
        Automatically detect AJAX dan return appropriate response:
            - AJAX: JsonResponse
            - Non-AJAX: HttpResponse redirect
        
        Args:
            request: HttpRequest object
            success: Operation success status
            message: Message untuk user
            redirect_url: URL untuk redirect (name atau path)
            errors: Errors jika ada (optional)
            
        Returns:
            JsonResponse atau HttpResponse redirect
            
        Examples:
            >>> return AjaxHandler.handle_ajax_or_redirect(
            ...     request=request,
            ...     success=True,
            ...     message='Berhasil!',
            ...     redirect_url='archive:document_list'
            ... )
        """
        from django.shortcuts import redirect
        
        if AjaxHandler.is_ajax(request):
            if success:
                return AjaxHandler.success_redirect(message, redirect_url, request)
            else:
                return AjaxHandler.error(message, errors, request)
        else:
            # Non-AJAX: add message and redirect
            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)
            
            # Build redirect URL
            url = reverse(redirect_url) if ':' in redirect_url else redirect_url
            return redirect(url)