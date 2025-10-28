from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, FileResponse, Http404
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import transaction
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import Document, DocumentCategory, SPDDocument, DocumentActivity, Employee
from .forms import DocumentUploadForm, SPDDocumentForm, DocumentFilterForm, DocumentUpdateForm
from .serializers import DocumentSerializer, CategorySerializer, SPDSerializer
from .utils import log_activity, get_client_ip, rename_document_file
import logging

logger = logging.getLogger(__name__)


# ==================== TEMPLATE VIEWS ====================

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


@login_required
def document_list(request):
    """List all documents with filters"""
    documents = Document.objects.filter(is_deleted=False).select_related(
        'category', 'created_by'
    ).prefetch_related('spd_info__employee')
    
    # Initialize filter form
    filter_form = DocumentFilterForm(request.GET or None)
    
    # Apply filters
    if filter_form.is_valid():
        search = filter_form.cleaned_data.get('search')
        category = filter_form.cleaned_data.get('category')
        date_from = filter_form.cleaned_data.get('date_from')
        date_to = filter_form.cleaned_data.get('date_to')
        employee = filter_form.cleaned_data.get('employee')
        
        if search:
            documents = documents.filter(
                # Q(title__icontains=search) |
                Q(spd_info__employee__name__icontains=search) |
                Q(spd_info__destination__icontains=search) |
                Q(category__name__icontains=search)
            )
        
        if category:
            documents = documents.filter(
                Q(category=category) | Q(category__parent=category)
            )
        
        if date_from:
            documents = documents.filter(document_date__gte=date_from)
        
        if date_to:
            documents = documents.filter(document_date__lte=date_to)
        
        if employee:
            documents = documents.filter(spd_info__employee=employee)
    
    # Pagination
    paginator = Paginator(documents, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Categories for sidebar
    categories = DocumentCategory.objects.filter(
        parent__isnull=True
    ).prefetch_related('children')
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'filter_form': filter_form,
        'total_results': documents.count(),
    }
    
    return render(request, 'archive/document_list.html', context)


@login_required
def document_detail(request, document_id):
    """Document detail view with activities"""
    document = get_object_or_404(
        Document.objects.select_related('category', 'created_by'),
        id=document_id,
        is_deleted=False
    )
    
    # Log view activity
    log_activity(
        document=document,
        user=request.user,
        action_type='view',
        request=request
    )
    
    # Get SPD info if exists
    spd_info = None
    try:
        spd_info = document.spd_info # type: ignore
    except SPDDocument.DoesNotExist:
        pass
    
    # Get activities
    activities = document.activities.select_related('user').order_by('-created_at')[:50] # type: ignore
    
    context = {
        'document': document,
        'spd_info': spd_info,
        'activities': activities,
    }
    
    return render(request, 'archive/document_detail.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def document_upload(request):
    """Upload regular document (non-SPD)"""
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Create document
                    document = form.save(commit=False)
                    document.created_by = request.user
                    document.save()
                    
                    # Rename file
                    rename_document_file(document)
                    
                    # Log activity
                    log_activity(
                        document=document,
                        user=request.user,
                        action_type='create',
                        description=f'Dokumen berhasil diunggah: {document.title}',
                        request=request
                    )
                    
                    messages.success(request, 'Dokumen berhasil diunggah!')
                    return redirect('archive:document_detail', document_id=document.id)
                    
            except Exception as e:
                logger.error(f"Error uploading document: {str(e)}")
                messages.error(request, f'Gagal mengunggah dokumen: {str(e)}')
        else:
            messages.error(request, 'Form tidak valid. Periksa kembali input Anda.')
    else:
        form = DocumentUploadForm()
    
    context = {
        'form': form,
        'title': 'Unggah Dokumen',
    }
    
    return render(request, 'archive/modals/document_upload.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def spd_upload(request):
    """Upload SPD document with employee info"""
    if request.method == 'POST':
        form = SPDDocumentForm(request.POST, request.FILES)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Get SPD category
                    spd_category = DocumentCategory.objects.get(slug='spd')
                    
                    # Create document
                    document = Document.objects.create(
                        title=form.cleaned_data['title'],
                        file=form.cleaned_data['file'],
                        document_date=form.cleaned_data['document_date'],
                        category=spd_category,
                        created_by=request.user
                    )
                    
                    # Create SPD info
                    spd_info = SPDDocument.objects.create(
                        document=document,
                        employee=form.cleaned_data['employee'],
                        destination=form.cleaned_data['destination'],
                        destination_other=form.cleaned_data.get('destination_other', ''),
                        start_date=form.cleaned_data['start_date'],
                        end_date=form.cleaned_data['end_date']
                    )
                    
                    # Rename file with complete info
                    rename_document_file(document)
                    
                    # Log activity
                    log_activity(
                        document=document,
                        user=request.user,
                        action_type='create',
                        description=f'SPD berhasil diunggah: {spd_info.employee.name} ke {spd_info.get_destination_display_full()}',
                        request=request
                    )
                    
                    messages.success(request, 'Dokumen SPD berhasil diunggah!')
                    return redirect('archive:document_detail', document_id=document.id)
                    
            except Exception as e:
                logger.error(f"Error uploading SPD: {str(e)}")
                messages.error(request, f'Gagal mengunggah SPD: {str(e)}')
        else:
            messages.error(request, 'Form tidak valid. Periksa kembali input Anda.')
    else:
        form = SPDDocumentForm()
    
    context = {
        'form': form,
        'title': 'Unggah Dokumen SPD',
    }
    
    return render(request, 'archive/spd_upload.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def document_update(request, document_id):
    """Update document metadata"""
    document = get_object_or_404(Document, id=document_id, is_deleted=False)
    
    if request.method == 'POST':
        form = DocumentUpdateForm(request.POST, instance=document)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Save old values for logging
                    # old_title = document.title # type: ignore
                    old_date = document.document_date
                    
                    # Update document
                    document = form.save()
                    
                    # Rename file if date changed
                    if old_date != document.document_date:
                        rename_document_file(document)
                    
                    # Log activity
                    changes = []
                    # if old_title != document.title:
                    #     changes.append(f"Judul: '{old_title}' → '{document.title}'")
                    if old_date != document.document_date:
                        changes.append(f"Tanggal: {old_date} → {document.document_date}") # type: ignore
                    
                    log_activity(
                        document=document,
                        user=request.user,
                        action_type='update',
                        description=f'Dokumen diperbarui: {", ".join(changes)}', # type: ignore
                        request=request
                    )
                    
                    messages.success(request, 'Dokumen berhasil diperbarui!')
                    return redirect('archive:document_detail', document_id=document.id)
                    
            except Exception as e:
                logger.error(f"Error updating document: {str(e)}")
                messages.error(request, f'Gagal memperbarui dokumen: {str(e)}')
        else:
            messages.error(request, 'Form tidak valid. Periksa kembali input Anda.')
    else:
        form = DocumentUpdateForm(instance=document)
    
    context = {
        'form': form,
        'document': document,
        'title': 'Perbarui Dokumen',
    }
    
    return render(request, 'archive/document_update.html', context)


@login_required
@require_http_methods(["POST"])
def document_delete(request, document_id):
    """Soft delete document"""
    document = get_object_or_404(Document, id=document_id, is_deleted=False)
    
    try:
        with transaction.atomic():
            document.is_deleted = True
            document.deleted_at = timezone.now()
            document.save(update_fields=['is_deleted', 'deleted_at'])
            
            # Log activity
            log_activity(
                document=document,
                user=request.user,
                action_type='delete',
                description=f'Dokumen dihapus: {document.title}', # type: ignore
                request=request
            )
            
            messages.success(request, 'Dokumen berhasil dihapus!')
            
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        messages.error(request, f'Gagal menghapus dokumen: {str(e)}')
    
    return redirect('archive:document_list')


@login_required
def document_download(request, document_id):
    """Download document file"""
    document = get_object_or_404(Document, id=document_id, is_deleted=False)
    
    try:
        # Log download activity
        log_activity(
            document=document,
            user=request.user,
            action_type='download',
            description=f'Dokumen diunduh: {document.title}', # type: ignore
            request=request
        )
        
        # Return file
        response = FileResponse(
            document.file.open('rb'),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'attachment; filename="{document.file.name.split("/")[-1]}"'
        
        return response
        
    except Exception as e:
        logger.error(f"Error downloading document: {str(e)}")
        raise Http404("File tidak ditemukan")


@login_required
def document_preview(request, document_id):
    """Preview document in browser"""
    document = get_object_or_404(Document, id=document_id, is_deleted=False)
    
    try:
        # Log view activity (if not already logged recently)
        from datetime import timedelta
        recent_view = DocumentActivity.objects.filter(
            document=document,
            user=request.user,
            action_type='view',
            created_at__gte=timezone.now() - timedelta(minutes=5)
        ).exists()
        
        if not recent_view:
            log_activity(
                document=document,
                user=request.user,
                action_type='view',
                request=request
            )
        
        # Return file for inline viewing
        response = FileResponse(
            document.file.open('rb'),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'inline; filename="{document.file.name.split("/")[-1]}"'
        
        return response
        
    except Exception as e:
        logger.error(f"Error previewing document: {str(e)}")
        raise Http404("File tidak ditemukan")


@login_required
def category_documents(request, category_slug):
    """List documents by category"""
    category = get_object_or_404(DocumentCategory, slug=category_slug)
    
    # Get documents from this category and its children
    if category.parent:
        # Subcategory - get only from this category
        documents = Document.objects.filter(
            category=category,
            is_deleted=False
        )
    else:
        # Parent category - get from all children
        documents = Document.objects.filter(
            Q(category=category) | Q(category__parent=category),
            is_deleted=False
        )
    
    documents = documents.select_related('category', 'created_by').order_by('-document_date')
    
    # Pagination
    paginator = Paginator(documents, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Categories for sidebar
    categories = DocumentCategory.objects.filter(
        parent__isnull=True
    ).prefetch_related('children')
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'current_category': category,
        'total_results': documents.count(),
    }
    
    return render(request, 'archive/document_list.html', context)


@login_required
def search_documents(request):
    """Search documents via AJAX"""
    query = request.GET.get('q', '')
    
    if len(query) < 3:
        return JsonResponse({'results': []})
    
    documents = Document.objects.filter(
        Q(spd_info__employee__name__icontains=query) |
        Q(spd_info__destination__icontains=query) |
        Q(category__name__icontains=query),
        is_deleted=False
    ).select_related('category', 'created_by').prefetch_related('spd_info__employee')[:10]
    
    results = []
    for doc in documents:
        result = {
            'id': doc.id, # type: ignore
            'title': doc.title, # type: ignore
            'category': doc.category.name,
            'date': doc.document_date.strftime('%d/%m/%Y'),
            'url': f'/archive/documents/{doc.id}/', # type: ignore
        }
        
        # Add SPD specific info
        try:
            spd = doc.spd_info # type: ignore
            result['employee'] = spd.employee.name
            result['destination'] = spd.get_destination_display_full()
        except:
            pass
        
        results.append(result)
    
    return JsonResponse({'results': results})


# ==================== API VIEWS (REST Framework) ====================

class DocumentViewSet(viewsets.ModelViewSet):
    """API ViewSet for Documents"""
    queryset = Document.objects.filter(is_deleted=False).select_related(
        'category', 'created_by'
    ).prefetch_related('spd_info__employee')
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]
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
    permission_classes = [IsAuthenticated]
    
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
    permission_classes = [IsAuthenticated]
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