from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.http import JsonResponse, FileResponse, Http404, HttpResponse
from django.template.loader import render_to_string
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import transaction
from django.db.models.functions import TruncMonth # Digunakan di dashboard
from datetime import datetime, timedelta # Digunakan di dashboard
from functools import wraps

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response

from django_filters.rest_framework import DjangoFilterBackend

from apps.accounts.decorators import staff_required
from apps.accounts.permissions import IsStaffOrReadOnly

from .models import Document, DocumentCategory, SPDDocument, DocumentActivity, Employee
from .forms import DocumentFilterForm, DocumentForm, DocumentUpdateForm, SPDDocumentForm, SPDDocumentUpdateForm, EmployeeForm
from .serializers import DocumentSerializer, CategorySerializer, SPDSerializer
from .utils import log_activity, rename_document_file, get_client_ip
import logging

logger = logging.getLogger(__name__)


def staff_required(function=None, redirect_url='/accounts/login/'):
    """
    Decorator untuk memastikan user adalah staff
    FIXED VERSION - properly wraps and calls the view function
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, 'Anda harus login terlebih dahulu.')
                return redirect(redirect_url)
            
            if not request.user.is_staff:
                messages.error(request, 'Anda tidak memiliki akses ke halaman ini.')
                return redirect('archive:dashboard')
            
            # CRITICAL: Actually call the view function and return its response
            return view_func(request, *args, **kwargs)
        
        return _wrapped_view
    
    if function:
        return decorator(function)
    
    return decorator


# ==================== DASHBOARD VIEWS ====================

# Dashboard old logic
@login_required
def dashboard(request):
    """Main dashboard view"""
    # Get statistics
    total_documents = Document.objects.filter(is_deleted=False).count()
    
    spd_category = DocumentCategory.objects.filter(slug='spd').first()
    total_spd = Document.objects.filter(
        category=spd_category,
        is_deleted=False
    ).count() if spd_category else 0
    
    belanjaan_category = DocumentCategory.objects.filter(slug='belanjaan').first()
    total_belanjaan = Document.objects.filter(
        category__parent=belanjaan_category,
        is_deleted=False
    ).count() if belanjaan_category else 0
    
    # Recent documents
    recent_documents = Document.objects.filter(
        is_deleted=False
    ).select_related('category', 'created_by').order_by('-created_at')[:10]
    
    # Recent activities
    recent_activities = DocumentActivity.objects.select_related(
        'document', 'user'
    ).order_by('-created_at')[:20]
    
    # Category statistics
    category_stats = DocumentCategory.objects.filter(
        parent__isnull=False
    ).annotate(
        doc_count=Count('documents', filter=Q(documents__is_deleted=False))
    ).order_by('-doc_count')
    
    # Monthly upload stats (last 6 months)
    from django.db.models.functions import TruncMonth
    from datetime import datetime, timedelta
    
    six_months_ago = timezone.now() - timedelta(days=180)
    monthly_stats = Document.objects.filter(
        created_at__gte=six_months_ago,
        is_deleted=False
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    context = {
        'total_documents': total_documents,
        'total_spd': total_spd,
        'total_belanjaan': total_belanjaan,
        'recent_documents': recent_documents,
        'recent_activities': recent_activities,
        'category_stats': category_stats,
        'monthly_stats': monthly_stats,
    }
    
    return render(request, 'archive/dashboard.html', context)


# ==================== TEMPLATE VIEWS ====================

# List updated logic
@login_required
def document_list(request, category_slug=None):
    """
    List all documents with filters
    
    Args:
        category_slug: Optional slug untuk filter by category via URL
    
    Features:
        - URL-based category filter (dari sidebar)
        - Form-based filters (search, date range, employee)
        - Pagination
        - Support parent + children categories
    """
    documents = Document.objects.filter(is_deleted=False).select_related(
        'category', 'created_by'
    ).prefetch_related('spd_info__employee').order_by('-document_date', '-created_at')

    current_category = None

    # Filter by category if slug provided (dari sidebar click)
    if category_slug: # type: ignore
        current_category = get_object_or_404(DocumentCategory, slug=category_slug) # type: ignore
        
        # Get documents from this category and all its children
        category_ids = [current_category.id] # type: ignore
        if current_category.children.exists(): # type: ignore
            category_ids.extend(current_category.children.values_list('id', flat=True)) # type: ignore
        
        documents = documents.filter(category_id__in=category_ids)

    # Initialize filter form
    filter_form = DocumentFilterForm(request.GET or None)
    
    # Apply filters
    if filter_form.is_valid():
        search = filter_form.cleaned_data.get('search')
        category = filter_form.cleaned_data.get('category')
        date_from = filter_form.cleaned_data.get('date_from')
        date_to = filter_form.cleaned_data.get('date_to')
        employee = filter_form.cleaned_data.get('employee')
        
        # Search filter
        if search:
            documents = documents.filter(
                Q(spd_info__employee__name__icontains=search) |
                Q(spd_info__destination__icontains=search) |
                Q(category__name__icontains=search) |
                Q(file__icontains=search)
            )
        
        # Category filter dari form (jika tidak ada URL category)
        # Form category filter akan override URL category filter
        if category:
            documents = documents.filter(
                Q(category=category) | Q(category__parent=category)
            )
        
        # Date range filter
        if date_from:
            documents = documents.filter(document_date__gte=date_from)
        
        if date_to:
            documents = documents.filter(document_date__lte=date_to)
        
        # Employee filter (for SPD)
        if employee:
            documents = documents.filter(spd_info__employee=employee)

    # Pagination
    paginator = Paginator(documents, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'current_category': current_category,
        'filter_form': filter_form,
        'total_results': documents.count(),
    }
    
    return render(request, 'archive/document_list.html', context)


@login_required
def search_documents(request):
    return HttpResponse("<h1>Halaman ini masih dalam pengembangan 🚧</h1>")

# ==================== DOCUMENT CRUD ====================

@staff_required
@require_http_methods(["GET", "POST"])
def document_create(request):
    """
    Handle upload dokumen belanjaan (CREATE)
    Support AJAX: return JSON with form HTML
    """
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Save document
                    document = form.save(commit=False)
                    document.created_by = request.user
                    document.save()
                    
                    # Auto rename file sesuai standar
                    rename_document_file(document)
                    
                    # Log activity menggunakan utils
                    log_activity(
                        document=document,
                        user=request.user,
                        action_type='create',
                        description=f'Dokumen {document.get_display_name()} dibuat',
                        request=request
                    )
                
                messages.success(request, f'Dokumen "{document.get_display_name()}" berhasil diupload!')
                
                # Return JSON for AJAX
                if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': 'Dokumen berhasil diupload!',
                        'redirect_url': request.build_absolute_uri('/documents/')
                    })
                
                return redirect('archive:document_list')
            
            except Exception as e:
                messages.error(request, f'Gagal mengupload dokumen: {str(e)}')
                
                if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': f'Gagal mengupload dokumen: {str(e)}'
                    }, status=400)
        
        else:
            # Form invalid - return form with errors
            if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
                html = render_to_string('archive/forms/document_form_content.html', {
                    'form': form,
                    'is_update': False
                }, request=request)
                
                return JsonResponse({
                    'success': False,
                    'html': html,
                    'errors': form.errors
                })
    
    else:
        # GET request - return empty form
        form = DocumentForm()
        
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            html = render_to_string('archive/forms/document_form_content.html', {
                'form': form,
                'is_update': False
            }, request=request)
            
            return JsonResponse({
                'success': True,
                'html': html
            })
    
    # Fallback for non-AJAX (shouldn't happen with modal approach)
    return render(request, 'archive/modals/document_form.html', {
        'form': form,
        'is_update': False
    })


@staff_required
@require_http_methods(["GET", "POST"])
def document_update(request, pk):
    """
    Handle update dokumen belanjaan (UPDATE metadata only)
    Support AJAX: return JSON with form HTML
    """
    document = get_object_or_404(Document, pk=pk, is_deleted=False)
    
    # Check if it's SPD document
    if hasattr(document, 'spd_info'):
        messages.error(request, 'Untuk dokumen SPD, gunakan form edit SPD')
        
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'Untuk dokumen SPD, gunakan form edit SPD'
            }, status=400)
        
        return redirect('archive:document_list')
    
    if request.method == 'POST':
        # Use UPDATE form (no file field)
        form = DocumentUpdateForm(request.POST, instance=document)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Update document (file tidak bisa diganti)
                    updated_document = form.save(commit=False)
                    updated_document.version += 1
                    updated_document.save()
                    
                    # Rename file jika kategori atau tanggal berubah
                    rename_document_file(updated_document)
                    
                    # Log activity menggunakan utils
                    log_activity(
                        document=updated_document,
                        user=request.user,
                        action_type='update',
                        description=f'Dokumen {updated_document.get_display_name()} diperbarui',
                        request=request
                    )
                
                messages.success(request, f'Dokumen "{updated_document.get_display_name()}" berhasil diperbarui!')
                
                if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': 'Dokumen berhasil diperbarui!',
                        'redirect_url': request.build_absolute_uri('/documents/')
                    })
                
                return redirect('archive:document_list')
            
            except Exception as e:
                messages.error(request, f'Gagal memperbarui dokumen: {str(e)}')
                
                if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': f'Gagal memperbarui dokumen: {str(e)}'
                    }, status=400)
        
        else:
            if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
                html = render_to_string('archive/forms/document_form_content.html', {
                    'form': form,
                    'document': document,
                    'is_update': True
                }, request=request)
                
                return JsonResponse({
                    'success': False,
                    'html': html,
                    'errors': form.errors
                })
    
    else:
        # GET request - return form with existing data (no file field)
        form = DocumentUpdateForm(instance=document)
        
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            html = render_to_string('archive/forms/document_form_content.html', {
                'form': form,
                'document': document,
                'is_update': True
            }, request=request)
            
            return JsonResponse({
                'success': True,
                'html': html
            })
    
    return render(request, 'archive/modals/document_form.html', {
        'form': form,
        'document': document,
        'is_update': True
    })


@staff_required
@require_http_methods(["POST"])
def document_delete(request, pk):
    """
    Handle soft delete dokumen belanjaan
    """
    document = get_object_or_404(Document, pk=pk, is_deleted=False)
    
    # Check if it's SPD document
    if hasattr(document, 'spd_info'):
        messages.error(request, 'Untuk dokumen SPD, gunakan delete SPD')
        
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'Untuk dokumen SPD, gunakan delete SPD'
            }, status=400)
        
        return redirect('archive:document_list')
    
    try:
        with transaction.atomic():
            # Soft delete
            from django.utils import timezone
            document.is_deleted = True
            document.deleted_at = timezone.now()
            document.save()
            
            # Log activity menggunakan utils
            log_activity(
                document=document,
                user=request.user,
                action_type='delete',
                description=f'Dokumen {document.get_display_name()} dihapus',
                request=request
            )
        
        messages.success(request, f'Dokumen "{document.get_display_name()}" berhasil dihapus!')
        
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Dokumen berhasil dihapus!'
            })
    
    except Exception as e:
        messages.error(request, f'Gagal menghapus dokumen: {str(e)}')
        
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': f'Gagal menghapus dokumen: {str(e)}'
            }, status=400)
    
    return redirect('archive:document_list')


# ==================== SPD CRUD ====================

@staff_required
@require_http_methods(["GET", "POST"])
def spd_create(request):
    """
    Handle upload dokumen SPD (CREATE)
    Support AJAX: return JSON with form HTML
    """
    if request.method == 'POST':
        form = SPDDocumentForm(request.POST, request.FILES)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Get SPD category
                    spd_category = DocumentCategory.objects.get(slug='spd')
                    
                    # Create Document
                    document = Document.objects.create(
                        file=form.cleaned_data['file'],
                        document_date=form.cleaned_data['document_date'],
                        category=spd_category,
                        created_by=request.user
                    )
                    
                    # Create SPD metadata
                    spd = SPDDocument.objects.create(
                        document=document,
                        employee=form.cleaned_data['employee'],
                        destination=form.cleaned_data['destination'],
                        destination_other=form.cleaned_data.get('destination_other', ''),
                        start_date=form.cleaned_data['start_date'],
                        end_date=form.cleaned_data['end_date']
                    )
                    
                    # Auto rename file sesuai format SPD
                    rename_document_file(document)
                    
                    # Log activity menggunakan utils
                    log_activity(
                        document=document,
                        user=request.user,
                        action_type='create',
                        description=f'SPD {spd.employee.name} ke {spd.get_destination_display_full()} dibuat',
                        request=request
                    )
                
                messages.success(request, f'SPD "{document.get_display_name()}" berhasil diupload!')
                
                if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': 'SPD berhasil diupload!',
                        'redirect_url': request.build_absolute_uri('/documents/')
                    })
                
                return redirect('archive:document_list')
            
            except Exception as e:
                messages.error(request, f'Gagal mengupload SPD: {str(e)}')
                
                if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': f'Gagal mengupload SPD: {str(e)}'
                    }, status=400)
        
        else:
            if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
                html = render_to_string('archive/forms/spd_form_content.html', {
                    'form': form,
                    'is_update': False
                }, request=request)
                
                return JsonResponse({
                    'success': False,
                    'html': html,
                    'errors': form.errors
                })
    
    else:
        # GET request - return empty form
        form = SPDDocumentForm()
        
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            html = render_to_string('archive/forms/spd_form_content.html', {
                'form': form,
                'is_update': False
            }, request=request)
            
            return JsonResponse({
                'success': True,
                'html': html
            })
    
    return render(request, 'archive/modals/spd_form.html', {
        'form': form,
        'is_update': False
    })


@staff_required
@require_http_methods(["GET", "POST"])
def spd_update(request, pk):
    """
    Handle update dokumen SPD (UPDATE metadata only)
    Support AJAX: return JSON with form HTML
    """
    document = get_object_or_404(Document, pk=pk, is_deleted=False)
    
    # Check if document has SPD info
    if not hasattr(document, 'spd_info'):
        messages.error(request, 'Dokumen ini bukan SPD')
        
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'Dokumen ini bukan SPD'
            }, status=400)
        
        return redirect('archive:document_list')
    
    spd = document.spd_info # type: ignore
    
    if request.method == 'POST':
        # Use UPDATE form (no file field)
        form = SPDDocumentUpdateForm(request.POST)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Update Document metadata
                    document.document_date = form.cleaned_data['document_date']
                    document.version += 1
                    document.save()
                    
                    # Update SPD metadata
                    spd.employee = form.cleaned_data['employee']
                    spd.destination = form.cleaned_data['destination']
                    spd.destination_other = form.cleaned_data.get('destination_other', '')
                    spd.start_date = form.cleaned_data['start_date']
                    spd.end_date = form.cleaned_data['end_date']
                    spd.save()
                    
                    # Rename file jika ada perubahan metadata
                    rename_document_file(document)
                    
                    # Log activity menggunakan utils
                    log_activity(
                        document=document,
                        user=request.user,
                        action_type='update',
                        description=f'SPD {spd.employee.name} ke {spd.get_destination_display_full()} diperbarui',
                        request=request
                    )
                
                messages.success(request, f'SPD "{document.get_display_name()}" berhasil diperbarui!')
                
                if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': 'SPD berhasil diperbarui!',
                        'redirect_url': request.build_absolute_uri('/documents/')
                    })
                
                return redirect('archive:document_list')
            
            except Exception as e:
                messages.error(request, f'Gagal memperbarui SPD: {str(e)}')
                
                if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': f'Gagal memperbarui SPD: {str(e)}'
                    }, status=400)
        
        else:
            if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
                html = render_to_string('archive/forms/spd_form_content.html', {
                    'form': form,
                    'spd': spd,
                    'document': document,
                    'is_update': True
                }, request=request)
                
                return JsonResponse({
                    'success': False,
                    'html': html,
                    'errors': form.errors
                })
    
    else:
        # GET request - populate form with existing data
        initial_data = {
            'document_date': document.document_date,
            'employee': spd.employee.id,
            'destination': spd.destination,
            'destination_other': spd.destination_other,
            'start_date': spd.start_date,
            'end_date': spd.end_date,
        }
        form = SPDDocumentForm(initial=initial_data)
        # File field tidak bisa diganti (metadata only)
        form.fields['file'].required = False
        form.fields['file'].widget.attrs['disabled'] = True
        form.fields['file'].help_text = 'File tidak dapat diganti saat edit. Hanya metadata yang dapat diubah.'
        
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            html = render_to_string('archive/forms/spd_form_content.html', {
                'form': form,
                'spd': spd,
                'document': document,
                'is_update': True
            }, request=request)
            
            return JsonResponse({
                'success': True,
                'html': html
            })
    
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
    Handle soft delete dokumen SPD
    """
    document = get_object_or_404(Document, pk=pk, is_deleted=False)
    
    # Check if document has SPD info
    if not hasattr(document, 'spd_info'):
        messages.error(request, 'Dokumen ini bukan SPD')
        
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'Dokumen ini bukan SPD'
            }, status=400)
        
        return redirect('archive:document_list')
    
    try:
        with transaction.atomic():
            # Soft delete
            from django.utils import timezone
            document.is_deleted = True
            document.deleted_at = timezone.now()
            document.save()
            
            # Log activity menggunakan utils
            log_activity(
                document=document,
                user=request.user,
                action_type='delete',
                description=f'SPD {document.get_display_name()} dihapus',
                request=request
            )
        
        messages.success(request, f'SPD "{document.get_display_name()}" berhasil dihapus!')
        
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'SPD berhasil dihapus!'
            })
    
    except Exception as e:
        messages.error(request, f'Gagal menghapus SPD: {str(e)}')
        
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': f'Gagal menghapus SPD: {str(e)}'
            }, status=400)
    
    return redirect('archive:document_list')


# ==================== VIEWS LAMA ====================

@login_required
def document_detail(request, document_id):
    return HttpResponse("<h1>Halaman ini masih dalam pengembangan 🚧</h1>")


@login_required
def document_download(request, document_id):
    return HttpResponse("<h1>Halaman ini masih dalam pengembangan 🚧</h1>")


@login_required
def document_preview(request, document_id):
    return HttpResponse("<h1>Halaman ini masih dalam pengembangan 🚧</h1>")


# ==================== API VIEWS (REST Framework) ====================

class DocumentViewSet(viewsets.ModelViewSet):
    """
    API endpoint for documents.
    Read-only for all users, Write access for 'Staff' only.
    """    
    queryset = Document.objects.filter(is_deleted=False).select_related(
        'category', 'created_by'
    ).prefetch_related('spd_info__employee')
    serializer_class = DocumentSerializer
    permission_classes = [IsStaffOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'document_date', 'created_by']
    search_fields = ['spd_info__employee__name', 'spd_info__destination', 'category__name']
    ordering_fields = ['document_date', 'created_at']
    ordering = ['-document_date']
    
    def perform_create(self, serializer):
        document = serializer.save(created_by=self.request.user)
        
        # Log activity
        log_activity(
            document=document,
            user=self.request.user,
            action_type='create',
            request=self.request
        )
    
    def perform_update(self, serializer):
        document = serializer.save()
        
        # Log activity
        log_activity(
            document=document,
            user=self.request.user,
            action_type='update',
            request=self.request
        )
    
    @action(detail=True, methods=['get'])
    def activities(self, request, pk=None):
        """Get document activities"""
        document = self.get_object()
        activities = document.activities.select_related('user').order_by('-created_at')[:50]
        
        data = [{
            'id': activity.id,
            'action': activity.get_action_type_display(),
            'user': activity.user.full_name if activity.user else 'System',
            'description': activity.description,
            'created_at': activity.created_at,
        } for activity in activities]
        
        return Response(data)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download document via API"""
        document = self.get_object()
        
        # Log activity
        log_activity(
            document=document,
            user=request.user,
            action_type='download',
            request=request
        )
        
        return FileResponse(
            document.file.open('rb'),
            content_type='application/pdf',
            as_attachment=True,
            filename=document.file.name.split('/')[-1]
        )


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """API ViewSet for Categories"""
    queryset = DocumentCategory.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsStaffOrReadOnly]
    
    @action(detail=True, methods=['get'])
    def documents(self, request, pk=None):
        """Get documents by category"""
        category = self.get_object()
        
        if category.parent:
            documents = Document.objects.filter(category=category, is_deleted=False)
        else:
            documents = Document.objects.filter(
                Q(category=category) | Q(category__parent=category),
                is_deleted=False
            )
        
        documents = documents.select_related('category', 'created_by')
        serializer = DocumentSerializer(documents, many=True)
        
        return Response(serializer.data)


class SPDViewSet(viewsets.ModelViewSet):
    """API ViewSet for SPD Documents"""
    queryset = SPDDocument.objects.all().select_related(
        'document', 'employee', 'document__category', 'document__created_by'
    )
    serializer_class = SPDSerializer
    permission_classes = [IsStaffOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['employee', 'destination', 'start_date']
    search_fields = ['employee__name', 'destination', 'destination_other']
    ordering_fields = ['start_date', 'document__created_at']
    ordering = ['-start_date']


@login_required
def dashboard_stats_api(request):
    """API endpoint for dashboard statistics"""
    from django.db.models.functions import TruncMonth
    from datetime import timedelta
    
    # Basic stats
    total_documents = Document.objects.filter(is_deleted=False).count()
    
    spd_category = DocumentCategory.objects.filter(slug='spd').first()
    total_spd = Document.objects.filter(
        category=spd_category,
        is_deleted=False
    ).count() if spd_category else 0
    
    belanjaan_category = DocumentCategory.objects.filter(slug='belanjaan').first()
    total_belanjaan = Document.objects.filter(
        category__parent=belanjaan_category,
        is_deleted=False
    ).count() if belanjaan_category else 0
    
    # Monthly stats (last 12 months)
    twelve_months_ago = timezone.now() - timedelta(days=365)
    monthly_stats = Document.objects.filter(
        created_at__gte=twelve_months_ago,
        is_deleted=False
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    # Category breakdown
    category_breakdown = DocumentCategory.objects.filter(
        parent__isnull=False
    ).annotate(
        doc_count=Count('documents', filter=Q(documents__is_deleted=False))
    ).values('name', 'doc_count')
    
    # Top uploaders
    top_uploaders = Document.objects.filter(
        is_deleted=False,
        created_at__gte=twelve_months_ago
    ).values(
        'created_by__full_name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    data = {
        'total_documents': total_documents,
        'total_spd': total_spd,
        'total_belanjaan': total_belanjaan,
        'monthly_stats': list(monthly_stats),
        'category_breakdown': list(category_breakdown),
        'top_uploaders': list(top_uploaders),
    }
    
    return JsonResponse(data)