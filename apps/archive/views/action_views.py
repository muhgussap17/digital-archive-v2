"""
Modul: views/action_views.py
Fungsi: Action views untuk document operations

Views:
    - document_detail: Load detail dokumen (AJAX)
    - document_activities: Load activity timeline (AJAX)
    - document_download: Download file PDF
    - document_preview: Preview PDF di browser

Catatan:
    - Views ini sudah menggunakan services layer
    - Hanya dipindahkan dari views.py
    - No refactoring needed
"""

import os
import logging
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, FileResponse, Http404
from django.template.loader import render_to_string
from django.contrib import messages
from django.shortcuts import render

from ..models import Document
from ..utils import log_document_activity

logger = logging.getLogger(__name__)


@login_required
def document_detail(request, pk):
    """
    View: Load Document Detail untuk Right Panel (AJAX)
    
    Returns:
        JsonResponse dengan HTML fragment untuk detail content
    """
    document = get_object_or_404(Document, pk=pk, is_deleted=False)
    
    try:
        context = {'document': document}
        
        detail_html = render_to_string(
            'archive/includes/document_detail_content.html',
            context,
            request=request
        )
        
        return JsonResponse({
            'success': True,
            'document_name': document.get_display_name(),
            'filename': document.get_filename(),
            'detail_html': detail_html
        })
        
    except Exception as e:
        logger.error(f'Error loading document detail {pk}: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': f'Gagal memuat detail: {str(e)}'
        }, status=500)


@login_required
def document_activities(request, pk):
    """
    View: Load Document Activities untuk Right Panel (AJAX)
    
    Returns:
        JsonResponse dengan HTML fragment untuk activity timeline
    """
    document = get_object_or_404(Document, pk=pk, is_deleted=False)
    
    try:
        activities = document.activities.select_related('user').order_by('-created_at')[:20] # type: ignore
        
        context = {
            'document': document,
            'activities': activities,
        }
        
        try:
            activity_html = render_to_string(
                'archive/includes/document_activity_content.html',
                context,
                request=request
            )
        except Exception as template_error:
            logger.error(f'Template render error: {str(template_error)}')
            activity_html = f'''
                <div class="text-center py-5">
                    <i class="fa-solid fa-exclamation-triangle fa-3x text-warning mb-3"></i>
                    <p class="text-muted">Gagal render aktivitas</p>
                </div>
            '''
        
        return JsonResponse({
            'success': True,
            'activity_html': activity_html
        })
        
    except Exception as e:
        logger.error(f'Error loading activities {pk}: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': f'Server error: {str(e)}'
        }, status=500)


@login_required
def document_download(request, pk):
    """
    View: Download Dokumen PDF
    
    Fitur:
        - Force download (attachment header)
        - Activity logging otomatis
        - Proper error handling
    """
    document = get_object_or_404(Document, pk=pk, is_deleted=False)
    
    try:
        if not document.file:
            messages.error(request, 'File dokumen tidak ditemukan.')
            return redirect('archive:document_list')
        
        file_path = document.file.path
        
        if not os.path.exists(file_path):
            messages.error(request, f'File tidak ditemukan: {document.get_filename()}')
            logger.error(f'File not found: {file_path}')
            return redirect('archive:document_list')
        
        # Log activity
        log_document_activity(
            document=document,
            user=request.user,
            action_type='download',
            description=f'Dokumen {document.get_filename()} diunduh',
            request=request
        )
        
        # Prepare response
        filename = document.get_filename()
        file_handle = document.file.open('rb')
        
        response = FileResponse(
            file_handle,
            content_type='application/pdf',
            as_attachment=True,
            filename=filename
        )
        
        response['Content-Length'] = document.file_size
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        logger.info(f'Document {pk} downloaded by {request.user.username}')
        
        return response
        
    except Exception as e:
        logger.error(f'Error downloading document {pk}: {str(e)}')
        messages.error(request, f'Gagal mengunduh dokumen: {str(e)}')
        return redirect('archive:document_list')


@login_required
def document_preview(request, pk):
    """
    View: Preview Dokumen PDF di Browser
    
    Fitur:
        - PDF.js viewer di modal
        - Cross-browser compatible
    """
    document = get_object_or_404(Document, pk=pk, is_deleted=False)
    
    try:
        if not document.file:
            messages.error(request, 'File dokumen tidak ditemukan.')
            return redirect('archive:document_list')
        
        file_path = document.file.path
        
        if not os.path.exists(file_path):
            messages.error(request, f'File tidak ditemukan: {document.get_filename()}')
            logger.error(f'File not found: {file_path}')
            return redirect('archive:document_list')
        
        # Get file URL untuk PDF.js
        file_url = document.file.url
        
        context = {
            'document': document,
            'file_url': file_url,
            'file_size_display': document.get_file_size_display(),
        }
        
        return render(request, 'archive/preview.html', context)
        
    except Exception as e:
        logger.error(f'Error previewing document {pk}: {str(e)}')
        messages.error(request, f'Gagal membuka preview: {str(e)}')
        return redirect('archive:document_list')