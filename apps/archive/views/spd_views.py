"""
Modul: views/spd_views.py
Fungsi: Views untuk SPD (Surat Perjalanan Dinas) CRUD operations (REFACTORED)

Views:
    - spd_create: Upload dokumen SPD baru
    - spd_update: Edit metadata SPD
    - spd_delete: Soft delete SPD

Improvement:
    - Business logic extracted ke SPDService
    - AJAX handling via AjaxHandler
    - Thin controllers (20-30 lines each)
    - Better separation of concerns

Implementasi Standar:
    - SPD melibatkan 2 models: Document + SPDDocument
    - Semua operations via service layer
    - Consistent error handling
    - Activity logging otomatis

Contoh Penggunaan:
>>> # Di urls.py
>>> from .views import spd_create, spd_update, spd_delete
>>> path('spd/create/', spd_create, name='spd_create')
"""

from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_http_methods

from apps.accounts.decorators import staff_required
from ..models import Document
from ..forms import SPDDocumentForm, SPDDocumentUpdateForm
from ..services import AjaxHandler, SPDService


@staff_required
@require_http_methods(["GET", "POST"])
def spd_create(request):
    """
    View: Upload Dokumen SPD Baru (REFACTORED)
    
    Fitur:
        - Upload PDF SPD dengan metadata lengkap
        - Auto rename dengan format: SPD_[PEGAWAI]_[TUJUAN]_[TANGGAL].pdf
        - Activity logging otomatis
        - Support AJAX modal
    
    Flow:
        GET  -> Return empty SPD form
        POST -> Validate -> Service create -> Redirect
    
    Permission:
        @staff_required - Hanya staff yang bisa upload SPD
    
    Catatan:
        - Business logic di SPDService.create_spd()
        - AJAX handling di AjaxHandler
        - Form fields: document_date, file, employee, destination, dates
    """
    # Initialize form
    form = SPDDocumentForm(request.POST or None, request.FILES or None)
    
    # POST: Process form submission
    if request.method == 'POST' and form.is_valid():
        try:
            # Call service layer for business logic
            document = SPDService.create_spd(
                form_data=form.cleaned_data,
                user=request.user,
                request=request
            )
            
            # Return success response (AJAX or redirect)
            return AjaxHandler.handle_ajax_or_redirect(
                request=request,
                success=True,
                message=f'SPD "{document.get_display_name()}" berhasil diupload!',
                redirect_url='archive:document_list'
            )
            
        except Exception as e:
            # Handle errors uniformly
            return AjaxHandler.handle_ajax_or_redirect(
                request=request,
                success=False,
                message=f'Gagal mengupload SPD: {str(e)}',
                redirect_url='archive:document_list'
            )
    
    # GET or invalid POST: Return form
    if AjaxHandler.is_ajax(request):
        return AjaxHandler.form_response(
            form=form,
            template='archive/forms/spd_form_content.html',
            context={'is_update': False},
            request=request,
            is_valid=form.is_valid() if request.method == 'POST' else True
        )
    
    # Fallback untuk non-AJAX request
    return render(request, 'archive/modals/spd_form.html', {
        'form': form,
        'is_update': False
    })


@staff_required
@require_http_methods(["GET", "POST"])
def spd_update(request, pk):
    """
    View: Edit Metadata Dokumen SPD (REFACTORED)
    
    Fitur:
        - Edit pegawai, tujuan, tanggal perjalanan
        - File tidak bisa diganti (metadata only)
        - Auto rename/relocate jika metadata berubah
        - Version tracking otomatis
        - Support AJAX modal
    
    Flow:
        GET  -> Return form dengan data SPD existing
        POST -> Validate -> Service update -> Redirect
    
    Permission:
        @staff_required - Hanya staff
    
    Catatan:
        - Hanya dokumen dengan spd_info yang bisa diedit via view ini
        - Business logic di SPDService.update_spd()
        - File field disabled pada form update
    """
    # Get document atau 404
    document = get_object_or_404(Document, pk=pk, is_deleted=False)
    
    # Validate document has SPD info
    if not hasattr(document, 'spd_info'):
        return AjaxHandler.handle_ajax_or_redirect(
            request=request,
            success=False,
            message='Dokumen ini bukan SPD',
            redirect_url='archive:document_list'
        )
    
    spd = document.spd_info # type: ignore
    
    # Initialize form
    if request.method == 'POST':
        form = SPDDocumentUpdateForm(request.POST)
    else:
        # Populate form dengan data existing
        initial_data = {
            'document_date': document.document_date,
            'employee': spd.employee.id,
            'destination': spd.destination,
            'destination_other': spd.destination_other,
            'start_date': spd.start_date,
            'end_date': spd.end_date,
        }
        form = SPDDocumentUpdateForm(initial=initial_data)
    
    # POST: Process form submission
    if request.method == 'POST' and form.is_valid():
        try:
            # Call service layer
            updated_document = SPDService.update_spd(
                document=document,
                form_data=form.cleaned_data,
                user=request.user,
                request=request
            )
            
            # Return success response
            return AjaxHandler.handle_ajax_or_redirect(
                request=request,
                success=True,
                message=f'SPD "{updated_document.get_display_name()}" berhasil diperbarui!',
                redirect_url='archive:document_list'
            )
            
        except Exception as e:
            return AjaxHandler.handle_ajax_or_redirect(
                request=request,
                success=False,
                message=f'Gagal memperbarui SPD: {str(e)}',
                redirect_url='archive:document_list'
            )
    
    # GET or invalid POST: Return form
    if AjaxHandler.is_ajax(request):
        return AjaxHandler.form_response(
            form=form,
            template='archive/forms/spd_form_content.html',
            context={
                'spd': spd,
                'document': document,
                'is_update': True
            },
            request=request,
            is_valid=form.is_valid() if request.method == 'POST' else True
        )
    
    # Fallback
    return render(request, 'archive/modals/spd_form.html', {
        'form': form,
        'spd': spd,
        'document': document,
        'is_update': True
    })


@staff_required
@require_http_methods(["POST"])
def spd_delete(request, pk):
    """
    View: Hapus Dokumen SPD (Soft Delete) (REFACTORED)
    
    Fitur:
        - Soft delete (is_deleted=True, deleted_at=timestamp)
        - File fisik tidak dihapus
        - Activity logging otomatis
        - Support AJAX
    
    Flow:
        POST -> Validate SPD -> Service delete -> Redirect
    
    Permission:
        @staff_required - Hanya staff
        POST only untuk keamanan
    
    Catatan:
        - Business logic di SPDService.delete_spd()
        - SPDDocument tetap tersimpan (OneToOne relation)
        - File bisa di-restore dengan set is_deleted=False
    """
    # Get document atau 404
    document = get_object_or_404(Document, pk=pk, is_deleted=False)
    
    # Validate document has SPD info
    if not hasattr(document, 'spd_info'):
        return AjaxHandler.handle_ajax_or_redirect(
            request=request,
            success=False,
            message='Dokumen ini bukan SPD',
            redirect_url='archive:document_list'
        )
    
    try:
        # Call service layer for soft delete
        SPDService.delete_spd(
            document=document,
            user=request.user,
            request=request
        )
        
        # Return success response
        return AjaxHandler.handle_ajax_or_redirect(
            request=request,
            success=True,
            message=f'SPD "{document.get_display_name()}" berhasil dihapus!',
            redirect_url='archive:document_list'
        )
        
    except Exception as e:
        return AjaxHandler.handle_ajax_or_redirect(
            request=request,
            success=False,
            message=f'Gagal menghapus SPD: {str(e)}',
            redirect_url='archive:document_list'
        )