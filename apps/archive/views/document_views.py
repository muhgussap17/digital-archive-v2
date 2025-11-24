"""
Modul: views/document_views.py
Fungsi: Views untuk Document CRUD operations (Refactored)

Views yang di-refactor:
    - document_create: Upload dokumen baru
    - document_update: Edit metadata dokumen
    - document_delete: Soft delete dokumen

Improvement:
    - Business logic extracted ke DocumentService
    - AJAX handling extracted ke AjaxHandler
    - Views menjadi thin controllers (15-30 lines each)
    - Easier to test dan maintain

Contoh Penggunaan:
>>> # Di urls.py
>>> path('documents/create/', document_views.document_create)
>>> path('documents/<int:pk>/update/', document_views.document_update)
"""

from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required

from apps.accounts.decorators import staff_required
from ..models import Document
from ..forms import DocumentForm, DocumentUpdateForm
from ..services import AjaxHandler, DocumentService


@staff_required
@require_http_methods(["GET", "POST"])
def document_create(request):
    """
    View: Upload Dokumen Belanjaan Baru (REFACTORED)
    
    Fitur:
        - Upload PDF dengan validasi
        - Auto rename file
        - Activity logging
        - Support AJAX modal
    
    Flow:
        GET  -> Return empty form
        POST -> Validate -> Service create -> Redirect
    
    Permission:
        @staff_required - Hanya staff
    
    Catatan:
        - Business logic di DocumentService.create_document()
        - AJAX handling di AjaxHandler
        - View hanya orchestrate HTTP layer
    """
    # Initialize form
    form = DocumentForm(request.POST or None, request.FILES or None)
    
    # POST: Process form
    if request.method == 'POST' and form.is_valid():
        try:
            # Call service layer (pure business logic)
            document = DocumentService.create_document(
                form_data=form.cleaned_data,
                file=request.FILES.get('file'),
                user=request.user,
                request=request
            )
            
            # Return success response
            return AjaxHandler.handle_ajax_or_redirect(
                request=request,
                success=True,
                message=f'Dokumen "{document.get_display_name()}" berhasil diupload!',
                redirect_url='archive:document_list'
            )
            
        except Exception as e:
            # Handle errors
            return AjaxHandler.handle_ajax_or_redirect(
                request=request,
                success=False,
                message=f'Gagal mengupload dokumen: {str(e)}',
                redirect_url='archive:document_list'
            )
    
    # GET or invalid POST: Return form
    if AjaxHandler.is_ajax(request):
        return AjaxHandler.form_response(
            form=form,
            template='archive/forms/document_form_content.html',
            context={'is_update': False},
            request=request,
            is_valid=form.is_valid() if request.method == 'POST' else True
        )
    
    # Fallback for non-AJAX
    from django.shortcuts import render
    return render(request, 'archive/modals/document_form.html', {
        'form': form,
        'is_update': False
    })


@staff_required
@require_http_methods(["GET", "POST"])
def document_update(request, pk):
    """
    View: Edit Metadata Dokumen (REFACTORED)
    
    Fitur:
        - Edit kategori dan tanggal
        - File tidak bisa diganti
        - Auto move file jika metadata berubah
        - Support AJAX modal
    
    Permission:
        @staff_required - Hanya staff
    
    Catatan:
        - SPD documents harus pakai spd_update
        - Business logic di DocumentService.update_document()
    """
    # Get document atau 404
    document = get_object_or_404(Document, pk=pk, is_deleted=False)
    
    # Check if SPD document
    if hasattr(document, 'spd_info'):
        return AjaxHandler.handle_ajax_or_redirect(
            request=request,
            success=False,
            message='Untuk dokumen SPD, gunakan form edit SPD',
            redirect_url='archive:document_list'
        )
    
    # Initialize form
    form = DocumentUpdateForm(
        request.POST or None,
        instance=document
    )
    
    # POST: Process form
    if request.method == 'POST' and form.is_valid():
        try:
            # Call service layer
            updated_document = DocumentService.update_document(
                document=document,
                form_data=form.cleaned_data,
                user=request.user,
                request=request
            )
            
            # Return success response
            return AjaxHandler.handle_ajax_or_redirect(
                request=request,
                success=True,
                message=f'Dokumen "{updated_document.get_display_name()}" berhasil diperbarui!',
                redirect_url='archive:document_list'
            )
            
        except Exception as e:
            return AjaxHandler.handle_ajax_or_redirect(
                request=request,
                success=False,
                message=f'Gagal memperbarui dokumen: {str(e)}',
                redirect_url='archive:document_list'
            )
    
    # GET or invalid POST: Return form
    if AjaxHandler.is_ajax(request):
        return AjaxHandler.form_response(
            form=form,
            template='archive/forms/document_form_content.html',
            context={'document': document, 'is_update': True},
            request=request,
            is_valid=form.is_valid() if request.method == 'POST' else True
        )
    
    # Fallback
    from django.shortcuts import render
    return render(request, 'archive/modals/document_form.html', {
        'form': form,
        'document': document,
        'is_update': True
    })


@staff_required
@require_http_methods(["POST"])
def document_delete(request, pk):
    """
    View: Hapus Dokumen (Soft Delete) (REFACTORED)
    
    Fitur:
        - Soft delete (is_deleted=True)
        - Activity logging
        - Support AJAX
    
    Permission:
        @staff_required - Hanya staff
        POST only untuk keamanan
    
    Catatan:
        - Business logic di DocumentService.delete_document()
        - File fisik tidak dihapus
    """
    # Get document atau 404
    document = get_object_or_404(Document, pk=pk, is_deleted=False)
    
    # Check if SPD
    if hasattr(document, 'spd_info'):
        return AjaxHandler.handle_ajax_or_redirect(
            request=request,
            success=False,
            message='Untuk dokumen SPD, gunakan delete SPD',
            redirect_url='archive:document_list'
        )
    
    try:
        # Call service layer
        DocumentService.delete_document(
            document=document,
            user=request.user,
            request=request
        )
        
        # Return success
        return AjaxHandler.handle_ajax_or_redirect(
            request=request,
            success=True,
            message=f'Dokumen "{document.get_display_name()}" berhasil dihapus!',
            redirect_url='archive:document_list'
        )
        
    except Exception as e:
        return AjaxHandler.handle_ajax_or_redirect(
            request=request,
            success=False,
            message=f'Gagal menghapus dokumen: {str(e)}',
            redirect_url='archive:document_list'
        )