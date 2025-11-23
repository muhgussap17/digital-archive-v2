"""
Modul: Archive Views - Sistem Pengarsipan Dokumen Digital
Fungsi: Mengelola tampilan dan logika bisnis untuk sistem pengarsipan dokumen pemerintah

Modul ini menyediakan fungsi-fungsi utama untuk:
- Dashboard monitoring dokumen
- Manajemen dokumen umum (CRUD)
- Manajemen dokumen SPD (Surat Perjalanan Dinas)
- Download dan preview dokumen
- REST API endpoints

Implementasi Standar:
- Sesuai dengan Django Best Practices 4.2+
- Mengikuti pola MVT (Model-View-Template) Django
- Menerapkan soft delete untuk keamanan data
- Activity logging untuk audit trail
- Permission-based access control

Contoh Penggunaan:
>>> # Di urls.py
>>> path('documents/', views.document_list, name='document_list')
>>> path('documents/create/', views.document_create, name='document_create')

Catatan Pemeliharaan:
- Semua operasi CRUD menggunakan transaction.atomic() untuk data integrity
- File handling menggunakan utility functions di utils.py
- Activity logging wajib pada setiap operasi penting
- Semua views yang mengubah data memerlukan @staff_required decorator
"""

import os
import logging
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

from .models import (
    Document, 
    DocumentCategory, 
    SPDDocument, 
    DocumentActivity, 
    Employee
)
from .forms import (
    DocumentForm, 
    DocumentUpdateForm, 
    SPDDocumentForm, 
    SPDDocumentUpdateForm, 
    DocumentFilterForm,
    EmployeeForm
)
from .serializers import DocumentSerializer, CategorySerializer, SPDSerializer
from .utils import (
    log_document_activity,     # RENAMED from log_activity
    rename_document_file,      # SAME
    extract_client_ip,         # RENAMED from get_client_ip
    relocate_document_file,    # RENAMED from move_document_file
)

# ==================== KONFIGURASI LOGGING ====================
# Setup logger untuk monitoring dan debugging
logger = logging.getLogger(__name__)

# ==================== SCRIPT TESTING (DEVELOPMENT ONLY) ====================
# Script ini untuk monitoring query database saat development
# PENTING: Hapus atau comment pada production!
# from django.db import connection
# from django.db import reset_queries
# reset_queries()



# ==================== DASHBOARD VIEWS ====================

# Dashboard old logic
@login_required
def dashboard(request):
    """
    View: Dashboard Utama Sistem Pengarsipan
    Fungsi: Menampilkan ringkasan statistik dan aktivitas terkini
    
    Fitur Utama:
    - Total dokumen per kategori (SPD, Belanjaan, dll)
    - Daftar dokumen terbaru (10 terakhir)
    - Log aktivitas pengguna (20 terakhir)
    - Statistik per kategori
    - Grafik upload bulanan (6 bulan terakhir)
    
    Implementasi Standar:
    - Query optimization dengan select_related dan prefetch_related
    - Filtering dengan Q objects untuk kompleks queries
    - Aggregate functions untuk statistik
    
    Args:
        request (HttpRequest): Objek request dari Django
    
    Returns:
        HttpResponse: Rendered template dashboard.html dengan context data
    
    Permission:
        @login_required - Hanya user yang sudah login
    
    Context Variables:
        total_documents (int): Total semua dokumen aktif
        total_spd (int): Total dokumen SPD
        total_belanjaan (int): Total dokumen belanjaan
        recent_documents (QuerySet): 10 dokumen terbaru
        recent_activities (QuerySet): 20 aktivitas terbaru
        category_stats (QuerySet): Statistik per kategori
        monthly_stats (QuerySet): Data upload per bulan
    
    Contoh Penggunaan:
    >>> # Di urls.py
    >>> path('dashboard/', views.dashboard, name='dashboard')
    >>> 
    >>> # Di template
    >>> <h3>Total Dokumen: {{ total_documents }}</h3>
    
    Catatan Pemeliharaan:
    - Query monthly_stats menggunakan TruncMonth, pastikan database support
    - Jika data dokumen sangat banyak, pertimbangkan caching
    - Filter is_deleted=False wajib ada di semua query
    """

    # ========== HITUNG STATISTIK UTAMA ==========
    # Total semua dokumen yang belum dihapus
    total_documents = Document.objects.filter(is_deleted=False).count()
    
    # Total dokumen SPD (Surat Perintah Dinas)
    spd_category = DocumentCategory.objects.filter(slug='spd').first()
    total_spd = Document.objects.filter(
        category=spd_category,
        is_deleted=False
    ).count() if spd_category else 0
    
    # Total dokumen belanjaan (semua sub-kategori di bawah Belanjaan)
    belanjaan_category = DocumentCategory.objects.filter(slug='belanjaan').first()
    total_belanjaan = Document.objects.filter(
        category__parent=belanjaan_category,
        is_deleted=False
    ).count() if belanjaan_category else 0
    
    # ========== DOKUMEN TERBARU ==========
    # Ambil 10 dokumen terakhir diupload
    # Gunakan select_related untuk menghindari N+1 query problem
    recent_documents = Document.objects.filter(
        is_deleted=False
    ).select_related(
        'category',      # Join dengan tabel category
        'created_by'     # Join dengan tabel user
    ).order_by('-created_at')[:10]
    
    # ========== LOG AKTIVITAS TERBARU ==========
    # Ambil 20 aktivitas terakhir untuk monitoring
    recent_activities = DocumentActivity.objects.select_related(
        'document',  # Join dengan tabel dokumen
        'user'       # Join dengan tabel user
    ).order_by('-created_at')[:20]
    
    # ========== STATISTIK PER KATEGORI ==========
    # Hitung jumlah dokumen per kategori (hanya sub-kategori)
    category_stats = DocumentCategory.objects.filter(
        parent__isnull=False  # Hanya kategori yang punya parent (sub-kategori)
    ).annotate(
        # Count dokumen dengan filter is_deleted=False
        doc_count=Count('documents', filter=Q(documents__is_deleted=False))
    ).order_by('-doc_count')
    
    # ========== STATISTIK UPLOAD BULANAN ==========
    # Data untuk grafik - 6 bulan terakhir
    six_months_ago = timezone.now() - timedelta(days=180)
    monthly_stats = Document.objects.filter(
        created_at__gte=six_months_ago,
        is_deleted=False
    ).annotate(
        # Truncate datetime ke bulan untuk grouping
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


def test(request):
    """
    View: Halaman Testing
    Fungsi: Untuk keperluan development dan testing fitur baru
    
    Catatan: Hapus atau comment pada production!
    """
    return render(request, 'archive/test.html')


# ==================== TEMPLATE VIEWS - DAFTAR DOKUMEN ====================

# List updated logic
@login_required
# Halaman umum
def document_list(request, category_slug=None):
    """
    View: Daftar Dokumen Umum (Non-SPD)
    Fungsi: Menampilkan list dokumen belanjaan dengan fitur filter dan pencarian
    
    Fitur Utama:
    - Filter berdasarkan kategori via URL slug
    - Filter berdasarkan form (search, tanggal, kategori)
    - Pencarian di nama kategori dan nama file
    - Pagination 5 item per halaman
    - Query optimization untuk performa
    
    Implementasi Standar:
    - Menggunakan select_related untuk join efisien
    - Filter bertingkat untuk kategori parent-child
    - Form validation dengan Django Forms
    - Pagination dengan Django Paginator
    
    Args:
        request (HttpRequest): Objek request dari Django
        category_slug (str, optional): Slug kategori untuk filter
    
    Returns:
        HttpResponse: Rendered template document_list.html
    
    Permission:
        @login_required - Hanya user yang sudah login
    
    Query Optimization:
        - select_related: category, category__parent, created_by
        - Total queries: 3-4 (documents + pagination + form)
    
    Contoh Penggunaan:
    >>> # Di urls.py
    >>> path('documents/', views.document_list, name='document_list')
    >>> path('documents/<slug:category_slug>/', views.document_list)
    >>> 
    >>> # Akses dengan filter kategori
    >>> /documents/belanja-modal/
    >>> 
    >>> # Akses dengan search
    >>> /documents/?search=atk&date_from=2024-01-01
    
    Catatan Pemeliharaan:
    - Filter form menggunakan DocumentFilterForm dengan is_spd=False
    - Kategori parent akan include semua child categories
    - Pagination number dapat diubah sesuai kebutuhan (default: 5)
    - Debug query script harus dihapus pada production
    """

    # ========== DEBUG SCRIPT (HAPUS PADA PRODUCTION) ==========
    # reset_queries()

    # ========== QUERY DASAR DOKUMEN ==========
    # Ambil semua dokumen yang belum dihapus
    # Gunakan select_related untuk menghindari N+1 queries
    documents = (
        Document.objects
        .filter(is_deleted=False)
        .select_related(
            'category',          # Join dengan kategori dokumen
            'category__parent',  # Join dengan parent kategori
            'created_by'         # Join dengan user yang upload
        )
        .order_by('-document_date', '-created_at')  # Urutkan terbaru
    )

    current_category = None

    # ========== FILTER BERDASARKAN KATEGORI DARI URL ==========
    if category_slug:
        # Ambil kategori berdasarkan slug, atau 404 jika tidak ada
        current_category = get_object_or_404(DocumentCategory, slug=category_slug)
        category_ids = [current_category.id] # type: ignore

        # Include semua child categories jika ada
        # Contoh: kategori "Belanjaan" akan include "Belanja Modal", "Belanja Barang", dll
        if current_category.children.exists(): # type: ignore
            category_ids.extend(
                current_category.children.values_list('id', flat=True) # type: ignore
            )
        
        # Filter dokumen berdasarkan list kategori
        documents = documents.filter(category_id__in=category_ids)

    # ========== INISIALISASI FORM FILTER ==========
    # Parameter is_spd=False karena ini untuk dokumen umum (non-SPD)
    filter_form = DocumentFilterForm(request.GET or None, is_spd=False)

    # ========== APPLY FILTER DARI FORM ==========
    if filter_form.is_valid():
        # Ambil cleaned data dari form
        search = filter_form.cleaned_data.get('search')
        category = filter_form.cleaned_data.get('category')
        date_from = filter_form.cleaned_data.get('date_from')
        date_to = filter_form.cleaned_data.get('date_to')
        
        # --- FILTER: PENCARIAN ---
        # Search di nama kategori dan nama file
        if search:
            documents = documents.filter(
                Q(category__name__icontains=search) |  # Cari di nama kategori
                Q(file__icontains=search)              # Cari di nama file
            )
        
        # --- FILTER: KATEGORI ---
        # Kategori dari form akan override filter URL
        if category:
            category_ids = [category.id]
            # Include child categories jika ada
            if category.children.exists():
                category_ids.extend(
                    category.children.values_list('id', flat=True)
                )
            documents = documents.filter(category_id__in=category_ids)

        # --- FILTER: TANGGAL MULAI ---
        if date_from:
            documents = documents.filter(document_date__gte=date_from)
        
        # --- FILTER: TANGGAL AKHIR ---
        if date_to:
            documents = documents.filter(document_date__lte=date_to)

    # ========== DEBUG: PRINT TOTAL QUERIES (HAPUS PADA PRODUCTION) ==========
    # print(f"Total queries: {len(connection.queries)}")
    # for query in connection.queries:
    #     print(f"{query['time']}s: {query['sql'][:100]}")

    context = {
        'page_obj': Paginator(documents, 10).get_page(request.GET.get('page')),
        'current_category': current_category,
        'filter_form': filter_form,
        'total_results': documents.count(),
    }

    return render(request, 'archive/document_list.html', context)


# Halaman SPD
def spd_list(request):
    """
    View: Daftar Dokumen SPD (Surat Perjalanan Dinas)
    Fungsi: Menampilkan list dokumen SPD dengan fitur filter khusus
    
    Fitur Utama:
    - Filter berdasarkan pegawai
    - Filter berdasarkan tujuan perjalanan dinas
    - Pencarian nama pegawai atau tujuan
    - Filter range tanggal
    - Pagination 5 item per halaman
    - Query optimization dengan join
    
    Implementasi Standar:
    - Menggunakan select_related untuk join efisien
    - Form khusus SPD dengan is_spd=True
    - Support pencarian di destination dan destination_other
    
    Args:
        request (HttpRequest): Objek request dari Django
    
    Returns:
        HttpResponse: Rendered template spd_list.html
    
    Permission:
        @login_required - Hanya user yang sudah login
    
    Query Optimization:
        - select_related: category, created_by, spd_info__employee
        - Total queries: 2-3 (documents + pagination + form data)
    
    Contoh Penggunaan:
    >>> # Di urls.py
    >>> path('spd/', views.spd_list, name='spd_list')
    >>> 
    >>> # Akses dengan filter
    >>> /spd/?employee=1&date_from=2024-01-01
    >>> /spd/?search=Jakarta&destination=jakarta
    
    Catatan Pemeliharaan:
    - Filter form menggunakan is_spd=True untuk field khusus SPD
    - Destination filter mencari di field destination DAN destination_other
    - spd_info adalah OneToOne relation, pastikan sudah di-join
    """

    # ========== DEBUG SCRIPT (HAPUS PADA PRODUCTION) ==========
    # reset_queries()

    # ========== QUERY DASAR DOKUMEN SPD ==========
    documents = (
        Document.objects
        .filter(
            is_deleted=False,
            category__slug='spd'  # Hanya dokumen dengan kategori SPD
        )
        .select_related(
            'category',            # Join dengan kategori
            'created_by',          # Join dengan user yang upload
            'spd_info__employee'   # Join dengan data SPD dan pegawai
        )
        .order_by('-document_date', '-created_at')
    )

    # ========== INISIALISASI FORM FILTER SPD ==========
    # Parameter is_spd=True untuk munculkan field employee dan destination
    filter_form = DocumentFilterForm(request.GET or None, is_spd=True)

    # ========== APPLY FILTER DARI FORM ==========
    if filter_form.is_valid():
        # Ambil cleaned data dari form
        search = filter_form.cleaned_data.get('search')
        employee = filter_form.cleaned_data.get('employee')
        destination = filter_form.cleaned_data.get('destination')
        date_from = filter_form.cleaned_data.get('date_from')
        date_to = filter_form.cleaned_data.get('date_to')
        
        # --- FILTER: PENCARIAN ---
        # Search di nama pegawai atau tujuan (destination / destination_other)
        if search:
            documents = documents.filter(
                Q(spd_info__employee__name__icontains=search) |        # Nama pegawai
                Q(spd_info__destination__icontains=search) |           # Tujuan pilihan
                Q(spd_info__destination_other__icontains=search)       # Tujuan lainnya
            )
        
        # --- FILTER: PEGAWAI ---
        if employee:
            documents = documents.filter(spd_info__employee=employee)
        
        # --- FILTER: TUJUAN ---
        # Filter bisa match destination ATAU destination_other
        if destination:
            documents = documents.filter(
                Q(spd_info__destination=destination) |
                Q(spd_info__destination_other__icontains=destination)
            )
        
        # --- FILTER: TANGGAL MULAI ---
        if date_from:
            documents = documents.filter(document_date__gte=date_from)
        
        # --- FILTER: TANGGAL AKHIR ---
        if date_to:
            documents = documents.filter(document_date__lte=date_to)
    
    # ========== DEBUG: PRINT QUERIES (HAPUS PADA PRODUCTION) ==========
    # print(f"Total queries: {len(connection.queries)}")
    # for query in connection.queries:
    #     print(f"  {query['time']}s: {query['sql'][:100]}")

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
    View: Halaman Pencarian Global
    Fungsi: Fitur pencarian menyeluruh di semua dokumen (under development)
    
    Status: UNDER DEVELOPMENT 🚧
    """
    return HttpResponse("<h1>Halaman ini masih dalam pengembangan 🚧</h1>")


# ==================== DOCUMENT CRUD - CREATE, UPDATE, DELETE ====================

@staff_required
@require_http_methods(["GET", "POST"])
def document_create(request):
    """
    View: Upload Dokumen Belanjaan Baru
    Fungsi: Handle form upload dokumen umum (non-SPD) dengan AJAX support
    
    Fitur Utama:
    - Upload file PDF dengan validasi
    - Auto rename file sesuai standar penamaan
    - Activity logging otomatis
    - Support AJAX untuk modal form
    - Transaction atomic untuk data integrity
    
    Implementasi Standar:
    - Menggunakan Django Forms untuk validasi
    - Transaction.atomic() untuk rollback jika error
    - Utility function rename_document_file() untuk penamaan
    - Activity logging dengan log_document_activity() utils
    
    Args:
        request (HttpRequest): Objek request (GET/POST)
    
    Returns:
        JsonResponse: Jika AJAX request (modal)
        HttpResponse: Jika non-AJAX request
    
    Permission:
        @staff_required - Hanya staff yang bisa upload
        @require_http_methods(["GET", "POST"]) - Hanya GET dan POST
    
    Flow:
        GET  -> Return form kosong (HTML via AJAX)
        POST -> Validasi -> Save -> Rename -> Log -> Redirect
    
    Contoh Penggunaan:
    >>> # Di template dengan AJAX
    >>> $.ajax({
    >>>     url: '{% url "archive:document_create" %}',
    >>>     method: 'POST',
    >>>     data: formData,
    >>>     processData: false,
    >>>     contentType: false,
    >>>     success: function(response) {
    >>>         if (response.success) {
    >>>             window.location.href = response.redirect_url;
    >>>         }
    >>>     }
    >>> });
    
    Catatan Pemeliharaan:
    - File akan otomatis di-rename sesuai format: [KATEGORI]_[TANGGAL]_[RANDOM].pdf
    - Jika transaction gagal, file upload akan di-rollback
    - Activity log mencatat: user, IP address, timestamp, action
    - Form errors akan dikembalikan dalam format JSON untuk AJAX
    """
    
    if request.method == 'POST':
        # ========== VALIDASI FORM ==========
        form = DocumentForm(request.POST, request.FILES)
        
        if form.is_valid():
            try:
                # ========== PROSES PENYIMPANAN (ATOMIC TRANSACTION) ==========
                with transaction.atomic():
                    # Simpan dokumen (belum commit ke database)
                    document = form.save(commit=False)
                    document.created_by = request.user  # Set user yang upload
                    document.save()  # Commit ke database
                    
                    # Rename file sesuai standar penamaan
                    # Format: [KATEGORI]_[TANGGAL]_[RANDOM].pdf
                    rename_document_file(document)
                    
                    # Log aktivitas untuk audit trail
                    log_document_activity(
                        document=document,
                        user=request.user,
                        action_type='create',
                        description=f'Dokumen {document.get_display_name()} dibuat',
                        request=request
                    )
                
                # Success message untuk user
                messages.success(
                    request, 
                    f'Dokumen "{document.get_display_name()}" berhasil diupload!'
                )
                
                # ========== RETURN JSON UNTUK AJAX ==========
                if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': 'Dokumen berhasil diupload!',
                        'redirect_url': request.build_absolute_uri('/documents/')
                    })
                
                # Redirect untuk non-AJAX
                return redirect('archive:document_list')
            
            except Exception as e:
                # Handle error dan rollback transaction
                messages.error(request, f'Gagal mengupload dokumen: {str(e)}')
                
                if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': f'Gagal mengupload dokumen: {str(e)}'
                    }, status=400)
        
        else:
            # ========== FORM INVALID - RETURN ERRORS ==========
            if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
                # Render form dengan error messages
                html = render_to_string(
                    'archive/forms/document_form_content.html', 
                    {
                        'form': form,
                        'is_update': False
                    }, 
                    request=request
                )
                
                return JsonResponse({
                    'success': False,
                    'html': html,
                    'errors': form.errors
                })
    
    else:
        # ========== GET REQUEST - RETURN FORM KOSONG ==========
        form = DocumentForm()
        
        # Return HTML form untuk AJAX modal
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            html = render_to_string(
                'archive/forms/document_form_content.html', 
                {
                    'form': form,
                    'is_update': False
                }, 
                request=request
            )
            
            return JsonResponse({
                'success': True,
                'html': html
            })
    
    # Fallback untuk non-AJAX (seharusnya tidak terjadi dengan modal)
    return render(request, 'archive/modals/document_form.html', {
        'form': form,
        'is_update': False
    })


@staff_required
@require_http_methods(["GET", "POST"])
def document_update(request, pk):
    """
    View: Edit Metadata Dokumen Belanjaan
    Fungsi: Update informasi dokumen tanpa mengganti file
    
    Fitur Utama:
    - Edit metadata dokumen (kategori, tanggal)
    - File tidak bisa diganti (metadata only)
    - Auto move file jika kategori/tanggal berubah
    - Version increment otomatis
    - Activity logging
    - Support AJAX modal
    
    Implementasi Standar:
    - Menggunakan DocumentUpdateForm (no file field)
    - Transaction atomic untuk data integrity
    - relocate_document_file() untuk reorganisasi file
    
    Args:
        request (HttpRequest): Objek request
        pk (int): Primary key dokumen
    
    Returns:
        JsonResponse: Jika AJAX request
        HttpResponse: Jika non-AJAX request
    
    Permission:
        @staff_required - Hanya staff
        @require_http_methods(["GET", "POST"])
    
    Flow:
        GET  -> Return form dengan data existing
        POST -> Validasi -> Update -> Move file -> Log -> Redirect
    
    Contoh Penggunaan:
    >>> # Di template
    >>> <button onclick="editDocument({{ document.id }})">Edit</button>
    >>> 
    >>> # AJAX call
    >>> function editDocument(id) {
    >>>     $.ajax({
    >>>         url: '/documents/' + id + '/update/',
    >>>         method: 'GET',
    >>>         success: function(response) {
    >>>             $('#modalContent').html(response.html);
    >>>             $('#editModal').modal('show');
    >>>         }
    >>>     });
    >>> }
    
    Catatan Pemeliharaan:
    - Form UPDATE tidak punya field file (metadata only)
    - Jika kategori/tanggal berubah, file akan dipindah ke folder baru
    - Version number otomatis increment untuk tracking changes
    - Dokumen SPD tidak bisa diedit via view ini, harus via spd_update
    """
    
    # ========== GET DOKUMEN ATAU 404 ==========
    document = get_object_or_404(Document, pk=pk, is_deleted=False)
    
    # ========== CEK APAKAH DOKUMEN SPD ==========
    # Dokumen SPD harus diedit via form SPD khusus
    if hasattr(document, 'spd_info'):
        messages.error(request, 'Untuk dokumen SPD, gunakan form edit SPD')
        
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'Untuk dokumen SPD, gunakan form edit SPD'
            }, status=400)
        
        return redirect('archive:document_list')
    
    if request.method == 'POST':
        # ========== VALIDASI FORM UPDATE ==========
        # Gunakan form UPDATE (tanpa field file)
        form = DocumentUpdateForm(request.POST, instance=document)
        
        if form.is_valid():
            try:
                # ========== PROSES UPDATE (ATOMIC TRANSACTION) ==========
                with transaction.atomic():
                    # Update metadata dokumen
                    updated_document = form.save(commit=False)
                    updated_document.version += 1  # Increment version untuk tracking
                    updated_document.save()
                    
                    # Move dan rename file jika kategori/tanggal berubah
                    # File akan dipindah ke folder kategori yang baru
                    relocate_document_file(updated_document)
                    
                    # Log aktivitas
                    log_document_activity(
                        document=updated_document,
                        user=request.user,
                        action_type='update',
                        description=f'Dokumen {updated_document.get_display_name()} diperbarui',
                        request=request
                    )
                
                messages.success(
                    request, 
                    f'Dokumen "{updated_document.get_display_name()}" berhasil diperbarui!'
                )
                
                # Return JSON untuk AJAX
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
            # ========== FORM INVALID - RETURN ERRORS ==========
            if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
                html = render_to_string(
                    'archive/forms/document_form_content.html', 
                    {
                        'form': form,
                        'document': document,
                        'is_update': True
                    }, 
                    request=request
                )
                
                return JsonResponse({
                    'success': False,
                    'html': html,
                    'errors': form.errors
                })
    
    else:
        # ========== GET REQUEST - RETURN FORM DENGAN DATA EXISTING ==========
        # Form UPDATE tidak ada field file
        form = DocumentUpdateForm(instance=document)
        
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            html = render_to_string(
                'archive/forms/document_form_content.html', 
                {
                    'form': form,
                    'document': document,
                    'is_update': True
                }, 
                request=request
            )
            
            return JsonResponse({
                'success': True,
                'html': html
            })
    
    # Fallback untuk non-AJAX
    return render(request, 'archive/modals/document_form.html', {
        'form': form,
        'document': document,
        'is_update': True
    })


@staff_required
@require_http_methods(["POST"])
def document_delete(request, pk):
    """
    View: Hapus Dokumen Belanjaan (Soft Delete)
    Fungsi: Menandai dokumen sebagai deleted tanpa menghapus fisik dari database
    
    Fitur Utama:
    - Soft delete (is_deleted=True, deleted_at=timestamp)
    - File fisik tidak dihapus dari storage
    - Activity logging untuk audit trail
    - Support AJAX untuk modal konfirmasi
    
    Implementasi Standar:
    - Soft delete sesuai best practice data retention
    - Transaction atomic untuk data integrity
    - Activity log untuk compliance audit
    
    Args:
        request (HttpRequest): Objek request (POST only)
        pk (int): Primary key dokumen
    
    Returns:
        JsonResponse: Jika AJAX request
        HttpResponse: Redirect jika non-AJAX
    
    Permission:
        @staff_required - Hanya staff
        @require_http_methods(["POST"]) - Hanya POST untuk keamanan
    
    Alasan Soft Delete:
    - Compliance: Memenuhi persyaratan audit trail
    - Recovery: Dokumen bisa di-restore jika terhapus tidak sengaja
    - Legal: Menjaga history untuk keperluan hukum
    - Analytics: Data tetap bisa digunakan untuk reporting
    
    Contoh Penggunaan:
    >>> # Di template dengan AJAX
    >>> function deleteDocument(id) {
    >>>     if (confirm('Yakin ingin menghapus dokumen ini?')) {
    >>>         $.ajax({
    >>>             url: '/documents/' + id + '/delete/',
    >>>             method: 'POST',
    >>>             headers: {'X-CSRFToken': csrfToken},
    >>>             success: function(response) {
    >>>                 location.reload();
    >>>             }
    >>>         });
    >>>     }
    >>> }
    
    Catatan Pemeliharaan:
    - File fisik TIDAK dihapus, hanya flag is_deleted=True
    - Untuk hapus permanen, buat cronjob cleanup terpisah
    - Dokumen SPD tidak bisa dihapus via view ini
    - Consider membuat view restore untuk recovery
    """
    
    # ========== GET DOKUMEN ATAU 404 ==========
    document = get_object_or_404(Document, pk=pk, is_deleted=False)
    
    # ========== CEK APAKAH DOKUMEN SPD ==========
    # Dokumen SPD harus dihapus via endpoint khusus SPD
    if hasattr(document, 'spd_info'):
        messages.error(request, 'Untuk dokumen SPD, gunakan delete SPD')
        
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'Untuk dokumen SPD, gunakan delete SPD'
            }, status=400)
        
        return redirect('archive:document_list')
    
    try:
        # ========== PROSES SOFT DELETE (ATOMIC TRANSACTION) ==========
        with transaction.atomic():
            # Set flag deleted dan timestamp
            document.is_deleted = True
            document.deleted_at = timezone.now()
            document.save()
            
            # Log aktivitas untuk audit trail
            log_document_activity(
                document=document,
                user=request.user,
                action_type='delete',
                description=f'Dokumen {document.get_display_name()} dihapus',
                request=request
            )
        
        messages.success(
            request, 
            f'Dokumen "{document.get_display_name()}" berhasil dihapus!'
        )
        
        # Return JSON untuk AJAX
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Dokumen berhasil dihapus!'
            })
    
    except Exception as e:
        # Handle error
        messages.error(request, f'Gagal menghapus dokumen: {str(e)}')
        
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': f'Gagal menghapus dokumen: {str(e)}'
            }, status=400)
    
    return redirect('archive:document_list')


# ==================== SPD CRUD - KHUSUS SURAT PERINTAH DINAS ====================

@staff_required
@require_http_methods(["GET", "POST"])
def spd_create(request):
    """
    View: Upload Dokumen SPD (Surat Perintah Dinas) Baru
    Fungsi: Handle form upload dokumen SPD dengan metadata lengkap
    
    Fitur Utama:
    - Upload file PDF SPD
    - Input metadata: pegawai, tujuan, tanggal perjalanan
    - Auto rename file dengan format khusus SPD
    - Support destination pilihan + destination other
    - Activity logging otomatis
    - Support AJAX modal
    
    Implementasi Standar:
    - Menggunakan SPDDocumentForm untuk validasi
    - Create Document + SPDDocument dalam satu transaction
    - Auto assign ke kategori 'spd'
    - Format nama file: SPD_[PEGAWAI]_[TUJUAN]_[TANGGAL].pdf
    
    Args:
        request (HttpRequest): Objek request
    
    Returns:
        JsonResponse: Jika AJAX request
        HttpResponse: Jika non-AJAX
    
    Permission:
        @staff_required - Hanya staff
        @require_http_methods(["GET", "POST"])
    
    Flow:
        GET  -> Return form kosong SPD
        POST -> Validasi -> Create Document -> Create SPD -> Rename -> Log -> Redirect
    
    Data SPD yang Disimpan:
    - Document: file, document_date, category='spd', created_by
    - SPDDocument: employee, destination, destination_other, start_date, end_date
    
    Contoh Penggunaan:
    >>> # Di template
    >>> <button onclick="createSPD()">Tambah SPD</button>
    >>> 
    >>> # AJAX call
    >>> $.ajax({
    >>>     url: '{% url "archive:spd_create" %}',
    >>>     method: 'POST',
    >>>     data: formData,
    >>>     processData: false,
    >>>     contentType: false
    >>> });
    
    Catatan Pemeliharaan:
    - Kategori 'spd' harus sudah ada di database
    - Pegawai harus sudah terdaftar di model Employee
    - Destination bisa pilihan dropdown atau input manual (destination_other)
    - File naming format bisa disesuaikan di rename_document_file()
    """
    
    if request.method == 'POST':
        # ========== VALIDASI FORM SPD ==========
        form = SPDDocumentForm(request.POST, request.FILES)
        
        if form.is_valid():
            try:
                # ========== PROSES PENYIMPANAN (ATOMIC TRANSACTION) ==========
                with transaction.atomic():
                    # Ambil kategori SPD
                    spd_category = DocumentCategory.objects.get(slug='spd')
                    
                    # Create Document utama
                    document = Document.objects.create(
                        file=form.cleaned_data['file'],
                        document_date=form.cleaned_data['document_date'],
                        category=spd_category,
                        created_by=request.user
                    )
                    
                    # Create metadata SPD (OneToOne dengan Document)
                    spd = SPDDocument.objects.create(
                        document=document,
                        employee=form.cleaned_data['employee'],
                        destination=form.cleaned_data['destination'],
                        destination_other=form.cleaned_data.get('destination_other', ''),
                        start_date=form.cleaned_data['start_date'],
                        end_date=form.cleaned_data['end_date']
                    )
                    
                    # Rename file dengan format khusus SPD
                    # Format: SPD_[NAMA_PEGAWAI]_[TUJUAN]_[TANGGAL].pdf
                    rename_document_file(document)
                    
                    # Log aktivitas
                    log_document_activity(
                        document=document,
                        user=request.user,
                        action_type='create',
                        description=f'SPD {spd.employee.name} ke {spd.get_destination_display_full()} dibuat',
                        request=request
                    )
                
                messages.success(
                    request, 
                    f'SPD "{document.get_display_name()}" berhasil diupload!'
                )
                
                # Return JSON untuk AJAX
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
            # ========== FORM INVALID - RETURN ERRORS ==========
            if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
                html = render_to_string(
                    'archive/forms/spd_form_content.html', 
                    {
                        'form': form,
                        'is_update': False
                    }, 
                    request=request
                )
                
                return JsonResponse({
                    'success': False,
                    'html': html,
                    'errors': form.errors
                })
    
    else:
        # ========== GET REQUEST - RETURN FORM KOSONG ==========
        form = SPDDocumentForm()
        
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            html = render_to_string(
                'archive/forms/spd_form_content.html', 
                {
                    'form': form,
                    'is_update': False
                }, 
                request=request
            )
            
            return JsonResponse({
                'success': True,
                'html': html
            })
    
    # Fallback untuk non-AJAX
    return render(request, 'archive/modals/spd_form.html', {
        'form': form,
        'is_update': False
    })


@staff_required
@require_http_methods(["GET", "POST"])
def spd_update(request, pk):
    """
    View: Edit Metadata Dokumen SPD
    Fungsi: Update informasi SPD tanpa mengganti file
    
    Fitur Utama:
    - Edit metadata SPD (pegawai, tujuan, tanggal)
    - File tidak bisa diganti (metadata only)
    - Auto move file jika metadata berubah
    - Version increment otomatis
    - Activity logging
    - Support AJAX modal
    
    Implementasi Standar:
    - Menggunakan SPDDocumentUpdateForm (no file field)
    - Update Document dan SPDDocument dalam satu transaction
    - relocate_document_file() untuk reorganisasi jika perlu
    
    Args:
        request (HttpRequest): Objek request
        pk (int): Primary key dokumen
    
    Returns:
        JsonResponse: Jika AJAX request
        HttpResponse: Jika non-AJAX
    
    Permission:
        @staff_required - Hanya staff
        @require_http_methods(["GET", "POST"])
    
    Flow:
        GET  -> Return form dengan data SPD existing
        POST -> Validasi -> Update Document -> Update SPD -> Move -> Log -> Redirect
    
    Contoh Penggunaan:
    >>> # Di template
    >>> <button onclick="editSPD({{ document.id }})">Edit SPD</button>
    
    Catatan Pemeliharaan:
    - Hanya dokumen dengan spd_info yang bisa diedit via view ini
    - File field di-disable pada form update
    - Jika pegawai/tujuan berubah, file akan di-rename ulang
    - Version number increment untuk tracking changes
    """
    
    # ========== GET DOKUMEN ATAU 404 ==========
    document = get_object_or_404(Document, pk=pk, is_deleted=False)
    
    # ========== CEK APAKAH DOKUMEN MEMILIKI SPD INFO ==========
    if not hasattr(document, 'spd_info'):
        messages.error(request, 'Dokumen ini bukan SPD')
        
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'Dokumen ini bukan SPD'
            }, status=400)
        
        return redirect('archive:document_list')
    
    spd = document.spd_info  # type: ignore
    
    if request.method == 'POST':
        # ========== VALIDASI FORM UPDATE ==========
        form = SPDDocumentUpdateForm(request.POST)
        
        if form.is_valid():
            try:
                # ========== PROSES UPDATE (ATOMIC TRANSACTION) ==========
                with transaction.atomic():
                    # Update metadata Document
                    document.document_date = form.cleaned_data['document_date']
                    document.version += 1  # Increment version
                    document.save()
                    
                    # Update metadata SPD
                    spd.employee = form.cleaned_data['employee']
                    spd.destination = form.cleaned_data['destination']
                    spd.destination_other = form.cleaned_data.get('destination_other', '')
                    spd.start_date = form.cleaned_data['start_date']
                    spd.end_date = form.cleaned_data['end_date']
                    spd.save()
                    
                    # Move dan rename file jika ada perubahan metadata
                    relocate_document_file(document)
                    
                    # Log aktivitas
                    log_document_activity(
                        document=document,
                        user=request.user,
                        action_type='update',
                        description=f'SPD {spd.employee.name} ke {spd.get_destination_display_full()} diperbarui',
                        request=request
                    )
                
                messages.success(
                    request, 
                    f'SPD "{document.get_display_name()}" berhasil diperbarui!'
                )
                
                # Return JSON untuk AJAX
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
            # ========== FORM INVALID - RETURN ERRORS ==========
            if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
                html = render_to_string(
                    'archive/forms/spd_form_content.html', 
                    {
                        'form': form,
                        'spd': spd,
                        'document': document,
                        'is_update': True
                    }, 
                    request=request
                )
                
                return JsonResponse({
                    'success': False,
                    'html': html,
                    'errors': form.errors
                })
    
    else:
        # ========== GET REQUEST - POPULATE FORM DENGAN DATA EXISTING ==========
        initial_data = {
            'document_date': document.document_date,
            'employee': spd.employee.id,
            'destination': spd.destination,
            'destination_other': spd.destination_other,
            'start_date': spd.start_date,
            'end_date': spd.end_date,
        }
        form = SPDDocumentForm(initial=initial_data)
        
        # Disable field file (tidak bisa diganti)
        form.fields['file'].required = False
        form.fields['file'].widget.attrs['disabled'] = True
        form.fields['file'].help_text = 'File tidak dapat diganti saat edit. Hanya metadata yang dapat diubah.'
        
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            html = render_to_string(
                'archive/forms/spd_form_content.html', 
                {
                    'form': form,
                    'spd': spd,
                    'document': document,
                    'is_update': True
                }, 
                request=request
            )
            
            return JsonResponse({
                'success': True,
                'html': html
            })
    
    # Fallback untuk non-AJAX
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
    View: Hapus Dokumen SPD (Soft Delete)
    Fungsi: Menandai dokumen SPD sebagai deleted tanpa menghapus dari database
    
    Fitur Utama:
    - Soft delete SPD dan metadata terkait
    - File fisik tidak dihapus
    - Activity logging untuk audit
    - Support AJAX
    
    Implementasi Standar:
    - Sama seperti document_delete tapi khusus SPD
    - Cascade soft delete ke SPDDocument
    
    Args:
        request (HttpRequest): POST request
        pk (int): Primary key dokumen
    
    Returns:
        JsonResponse: Jika AJAX
        HttpResponse: Redirect jika non-AJAX
    
    Permission:
        @staff_required - Hanya staff
        @require_http_methods(["POST"])
    
    Catatan Pemeliharaan:
    - SPDDocument tetap tersimpan di database (karena OneToOne)
    - File fisik tidak dihapus
    - Untuk recovery, tinggal set is_deleted=False
    """
    
    # ========== GET DOKUMEN ATAU 404 ==========
    document = get_object_or_404(Document, pk=pk, is_deleted=False)
    
    # ========== CEK APAKAH DOKUMEN MEMILIKI SPD INFO ==========
    if not hasattr(document, 'spd_info'):
        messages.error(request, 'Dokumen ini bukan SPD')
        
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'Dokumen ini bukan SPD'
            }, status=400)
        
        return redirect('archive:document_list')
    
    try:
        # ========== PROSES SOFT DELETE (ATOMIC TRANSACTION) ==========
        with transaction.atomic():
            # Set flag deleted dan timestamp
            document.is_deleted = True
            document.deleted_at = timezone.now()
            document.save()
            
            # Log aktivitas
            log_document_activity(
                document=document,
                user=request.user,
                action_type='delete',
                description=f'SPD {document.get_display_name()} dihapus',
                request=request
            )
        
        messages.success(
            request, 
            f'SPD "{document.get_display_name()}" berhasil dihapus!'
        )
        
        # Return JSON untuk AJAX
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


# ==================== ACTIONS ====================

@login_required
def document_detail(request, pk):
    """
    Get document detail untuk right panel (AJAX)
    
    Returns JSON dengan HTML fragment untuk detail content
    """
    document = get_object_or_404(Document, pk=pk, is_deleted=False)
    
    try:
        # Prepare context
        context = {
            'document': document,
        }
        
        # Render detail HTML
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
    Get document activities untuk right panel (AJAX)
    
    Returns JSON dengan HTML fragment untuk activity timeline
    """
    document = get_object_or_404(Document, pk=pk, is_deleted=False)
    
    try:
        # Get activities (latest first)
        activities = document.activities.select_related('user').order_by('-created_at')[:20] # type: ignore
        
        # Prepare context
        context = {
            'document': document,
            'activities': activities,
        }
        
        # Render activity HTML dengan error handling
        try:
            activity_html = render_to_string(
                'archive/includes/document_activity_content.html',
                context,
                request=request
            )
        except Exception as template_error:
            logger.error(f'Template render error for activities {pk}: {str(template_error)}')
            # Return fallback HTML
            activity_html = f'''
                <div class="text-center py-5">
                    <i class="fa-solid fa-exclamation-triangle fa-3x text-warning mb-3"></i>
                    <p class="text-muted">Gagal render aktivitas</p>
                    <small class="text-muted">{str(template_error)}</small>
                </div>
            '''
        
        return JsonResponse({
            'success': True,
            'activity_html': activity_html
        })
        
    except Document.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Dokumen tidak ditemukan'
        }, status=404)
    except Exception as e:
        logger.error(f'Error loading document activities {pk}: {str(e)}')
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'message': f'Server error: {str(e)}'
        }, status=500)


@login_required
def document_download(request, pk):
    """
    Download dokumen PDF dengan force download
    
    Fitur:
        - Force download (attachment header)
        - Activity logging otomatis
        - Proper filename handling
        - Error handling komprehensif
        
    Args:
        pk (int): Primary key dokumen
        
    Returns:
        FileResponse: File PDF untuk download
        
    Raises:
        Http404: Jika dokumen tidak ditemukan atau sudah dihapus
        
    Permission:
        - Semua authenticated users
        
    Activity Log:
        - Log setiap download ke DocumentActivity
        - Track user, IP address, timestamp
        
    Implementasi Standar:
        Mengikuti best practice Django untuk file serving
        dengan proper headers dan error handling
    """
    
    # Debug script
    # reset_queries()
    
    # Get document atau 404
    document = get_object_or_404(Document, pk=pk, is_deleted=False)
    
    try:
        # Check if file exists
        if not document.file:
            messages.error(request, 'File dokumen tidak ditemukan.')
            return redirect('archive:document_list')
        
        # Get file path
        file_path = document.file.path
        
        if not os.path.exists(file_path):
            messages.error(request, f'File tidak ditemukan di server: {document.get_filename()}')
            logger.error(f'File not found: {file_path} for document {pk}')
            return redirect('archive:document_list')
        
        # Log activity menggunakan utils
        log_document_activity(
            document=document,
            user=request.user,
            action_type='download',
            description=f'Dokumen {document.get_display_name()} diunduh',
            request=request
        )
        
        # Get clean filename (handle Indonesian characters)
        filename = document.get_filename()
        
        # Open file dan prepare response
        file_handle = document.file.open('rb')
        
        # Create FileResponse dengan force download
        response = FileResponse(
            file_handle,
            content_type='application/pdf',
            as_attachment=True,  # Force download
            filename=filename
        )
        
        # Add additional headers untuk compatibility
        response['Content-Length'] = document.file_size
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        logger.info(f'Document {pk} downloaded by {request.user.username}')
        
        # Debug script
        # print(f"Total queries: {len(connection.queries)}")

        return response
        
    except Exception as e:
        logger.error(f'Error downloading document {pk}: {str(e)}')
        messages.error(request, f'Gagal mengunduh dokumen: {str(e)}')
        return redirect('archive:document_list')


@login_required
def document_preview(request, pk):
    """
    Preview dokumen PDF di browser (modal dengan PDF.js)
    
    Fitur:
        - Render halaman dengan modal PDF viewer
        - PDF.js untuk cross-browser compatibility
        - Activity logging (optional - view tracking)
        
    Args:
        pk (int): Primary key dokumen
        
    Returns:
        HttpResponse: Rendered template dengan PDF viewer modal
        
    Raises:
        Http404: Jika dokumen tidak ditemukan atau sudah dihapus
        
    Permission:
        - Semua authenticated users
        
    Activity Log:
        - Log view activity (optional, bisa dinonaktifkan)
        
    Implementasi Standar:
        Menggunakan PDF.js library untuk universal compatibility
        dan smooth rendering di semua browser modern
    """
    # Get document atau 404
    document = get_object_or_404(Document, pk=pk, is_deleted=False)
    
    try:
        # Check if file exists
        if not document.file:
            messages.error(request, 'File dokumen tidak ditemukan.')
            return redirect('archive:document_list')
        
        file_path = document.file.path
        
        if not os.path.exists(file_path):
            messages.error(request, f'File tidak ditemukan di server: {document.get_filename()}')
            logger.error(f'File not found: {file_path} for document {pk}')
            return redirect('archive:document_list')
        
        # Optional: Log view activity
        # Uncomment jika ingin track views
        # log_document_activity(
        #     document=document,
        #     user=request.user,
        #     action_type='view',
        #     description=f'Dokumen {document.get_display_name()} dilihat',
        #     request=request
        # )
        
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
        log_document_activity(
            document=document,
            user=self.request.user,
            action_type='create',
            request=self.request
        )
    
    def perform_update(self, serializer):
        document = serializer.save()
        
        # Log activity
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
        
        # Log activity
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