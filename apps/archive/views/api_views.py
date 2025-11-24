"""
Modul: views/api_views.py
Fungsi: Django REST Framework ViewSets dan API endpoints

ViewSets:
    - DocumentViewSet: CRUD API untuk documents
    - CategoryViewSet: Read-only API untuk categories
    - SPDViewSet: CRUD API untuk SPD documents

API Endpoints:
    - dashboard_stats_api: Statistics API untuk dashboard

Catatan:
    - Tidak perlu refactor (sudah bagus)
    - Hanya dipindahkan dari views.py
    - Permission: IsStaffOrReadOnly
"""

from datetime import timedelta
from django.http import JsonResponse, FileResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q, Count
from django.db.models.functions import TruncMonth

from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.accounts.permissions import IsStaffOrReadOnly
from ..models import Document, DocumentCategory, SPDDocument
from ..serializers import DocumentSerializer, CategorySerializer, SPDSerializer
from ..utils import log_document_activity


class DocumentViewSet(viewsets.ModelViewSet):
    """
    API ViewSet untuk Documents
    
    Endpoints:
        - GET /api/documents/ - List documents
        - POST /api/documents/ - Create document (staff only)
        - GET /api/documents/{id}/ - Detail document
        - PUT/PATCH /api/documents/{id}/ - Update (staff only)
        - DELETE /api/documents/{id}/ - Delete (staff only)
        - GET /api/documents/{id}/activities/ - Document activities
        - GET /api/documents/{id}/download/ - Download document
    
    Permissions:
        - Read: All authenticated users
        - Write: Staff only
    
    Filters:
        - category, document_date, created_by
    
    Search:
        - spd_info__employee__name, spd_info__destination, category__name
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
        """Log activity saat create document"""
        document = serializer.save(created_by=self.request.user)
        
        log_document_activity(
            document=document,
            user=self.request.user,
            action_type='create',
            request=self.request
        )
    
    def perform_update(self, serializer):
        """Log activity saat update document"""
        document = serializer.save()
        
        log_document_activity(
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
        
        log_document_activity(
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
    """
    API ViewSet untuk Categories (Read-only)
    
    Endpoints:
        - GET /api/categories/ - List categories
        - GET /api/categories/{id}/ - Detail category
        - GET /api/categories/{id}/documents/ - Documents in category
    """
    
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
    """
    API ViewSet untuk SPD Documents
    
    Endpoints:
        - GET /api/spd/ - List SPD documents
        - POST /api/spd/ - Create SPD (staff only)
        - GET /api/spd/{id}/ - Detail SPD
        - PUT/PATCH /api/spd/{id}/ - Update (staff only)
        - DELETE /api/spd/{id}/ - Delete (staff only)
    
    Permissions:
        - Read: All authenticated users
        - Write: Staff only
    
    Filters:
        - employee, destination, start_date
    
    Search:
        - employee__name, destination, destination_other
    """
    
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
    """
    API endpoint untuk dashboard statistics
    
    Returns:
        JsonResponse dengan data:
            - total_documents, total_spd, total_belanjaan
            - monthly_stats (12 bulan terakhir)
            - category_breakdown
            - top_uploaders (top 5)
    """
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