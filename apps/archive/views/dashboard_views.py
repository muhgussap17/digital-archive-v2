"""
Modul: views/dashboard_views.py
Fungsi: Dashboard, list, dan search views

Views:
    - dashboard: Main dashboard dengan statistik
    - document_list: List dokumen belanjaan dengan filter
    - spd_list: List dokumen SPD dengan filter
    - search_documents: Global search (under development)

Catatan:
    - Views ini tidak perlu refactor karena sudah documented dengan baik
    - Hanya dipindahkan dari views.py ke module terpisah
    - Query optimization sudah diterapkan
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models.functions import TruncMonth
from datetime import timedelta

from ..models import (
    Document,
    DocumentCategory,
    DocumentActivity,
)
from ..forms import DocumentFilterForm


@login_required
def dashboard(request):
    """
    View: Dashboard Utama Sistem Pengarsipan
    
    Fitur:
        - Total dokumen per kategori
        - Dokumen terbaru (10 terakhir)
        - Log aktivitas (20 terakhir)
        - Statistik per kategori
        - Grafik upload bulanan (6 bulan)
    
    Query Optimization:
        - select_related untuk avoid N+1 queries
        - Aggregate functions untuk statistik
    """
    # Statistik utama
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
    
    # Dokumen terbaru
    recent_documents = Document.objects.filter(
        is_deleted=False
    ).select_related('category', 'created_by').order_by('-created_at')[:10]
    
    # Aktivitas terbaru
    recent_activities = DocumentActivity.objects.select_related(
        'document', 'user'
    ).order_by('-created_at')[:20]
    
    # Statistik kategori
    category_stats = DocumentCategory.objects.filter(
        parent__isnull=False
    ).annotate(
        doc_count=Count('documents', filter=Q(documents__is_deleted=False))
    ).order_by('-doc_count')
    
    # Statistik bulanan
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
def document_list(request, category_slug=None):
    """
    View: List Dokumen Belanjaan dengan Filter
    
    Fitur:
        - Filter by category via URL
        - Search by name/file
        - Date range filter
        - Pagination (10 per page)
        - Query optimization
    """
    # Base query
    documents = Document.objects.filter(
        is_deleted=False
    ).select_related(
        'category', 'category__parent', 'created_by'
    ).order_by('-document_date', '-created_at')
    
    current_category = None
    
    # Filter by category dari URL
    if category_slug:
        current_category = get_object_or_404(DocumentCategory, slug=category_slug)
        category_ids = [current_category.id] # type: ignore
        
        if current_category.children.exists(): # type: ignore
            category_ids.extend(
                current_category.children.values_list('id', flat=True) # type: ignore
            )
        
        documents = documents.filter(category_id__in=category_ids)
    
    # Filter form
    filter_form = DocumentFilterForm(request.GET or None, is_spd=False)
    
    if filter_form.is_valid():
        search = filter_form.cleaned_data.get('search')
        category = filter_form.cleaned_data.get('category')
        date_from = filter_form.cleaned_data.get('date_from')
        date_to = filter_form.cleaned_data.get('date_to')
        
        if search:
            documents = documents.filter(
                Q(category__name__icontains=search) |
                Q(file__icontains=search)
            )
        
        if category:
            category_ids = [category.id]
            if category.children.exists():
                category_ids.extend(category.children.values_list('id', flat=True))
            documents = documents.filter(category_id__in=category_ids)
        
        if date_from:
            documents = documents.filter(document_date__gte=date_from)
        
        if date_to:
            documents = documents.filter(document_date__lte=date_to)
    
    context = {
        'page_obj': Paginator(documents, 10).get_page(request.GET.get('page')),
        'current_category': current_category,
        'filter_form': filter_form,
        'total_results': documents.count(),
    }
    
    return render(request, 'archive/document_list.html', context)


@login_required
def spd_list(request):
    """
    View: List Dokumen SPD dengan Filter Khusus
    
    Fitur:
        - Filter by employee
        - Filter by destination
        - Search by name/destination
        - Date range filter
        - Pagination (10 per page)
    """
    # Base query
    documents = Document.objects.filter(
        is_deleted=False,
        category__slug='spd'
    ).select_related(
        'category', 'created_by', 'spd_info__employee'
    ).order_by('-document_date', '-created_at')
    
    # Filter form (SPD mode)
    filter_form = DocumentFilterForm(request.GET or None, is_spd=True)
    
    if filter_form.is_valid():
        search = filter_form.cleaned_data.get('search')
        employee = filter_form.cleaned_data.get('employee')
        destination = filter_form.cleaned_data.get('destination')
        date_from = filter_form.cleaned_data.get('date_from')
        date_to = filter_form.cleaned_data.get('date_to')
        
        if search:
            documents = documents.filter(
                Q(spd_info__employee__name__icontains=search) |
                Q(spd_info__destination__icontains=search) |
                Q(spd_info__destination_other__icontains=search)
            )
        
        if employee:
            documents = documents.filter(spd_info__employee=employee)
        
        if destination:
            documents = documents.filter(
                Q(spd_info__destination=destination) |
                Q(spd_info__destination_other__icontains=destination)
            )
        
        if date_from:
            documents = documents.filter(document_date__gte=date_from)
        
        if date_to:
            documents = documents.filter(document_date__lte=date_to)
    
    context = {
        'page_obj': Paginator(documents, 10).get_page(request.GET.get('page')),
        'current_category': DocumentCategory.objects.get(slug='spd'),
        'filter_form': filter_form,
        'total_results': documents.count(),
    }
    
    return render(request, 'archive/spd_list.html', context)


@login_required
def search_documents(request):
    """
    View: Global Search (Under Development)
    
    Status: Placeholder untuk fitur future
    """
    return HttpResponse("<h1>Halaman ini masih dalam pengembangan 🚧</h1>")