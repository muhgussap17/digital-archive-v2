"""
Modul: apps/archive/serializers.py (REFACTORED)
Fungsi: REST API Serializers untuk Archive models

Berisi serializers untuk:
    - Employee: Master data pegawai
    - DocumentCategory: Kategori dokumen hierarki
    - SPDDocument: Metadata SPD dengan detail perjalanan
    - Document: Dokumen utama dengan full metadata
    - DocumentActivity: Audit trail aktivitas dokumen

Implementasi Standar:
    - DRF (Django Rest Framework) serializers
    - Optimized queries dengan select_related
    - Custom display methods untuk formatted output
    - Nested serializers untuk relasi
    - Read-only computed fields

Catatan Pemeliharaan:
    - Digunakan oleh REST API endpoints (/api/*)
    - ViewSets: DocumentViewSet, CategoryViewSet, SPDViewSet
    - Semua serializers readonly kecuali yang explicitly editable
    - URL generation untuk file access

Cara Penggunaan API:
    GET /api/documents/          → List semua dokumen
    GET /api/documents/{id}/     → Detail dokumen
    GET /api/categories/         → List kategori
    GET /api/spd/               → List SPD documents
    GET /api/dashboard/stats/   → Dashboard statistics
"""

from rest_framework import serializers
from .models import Document, DocumentCategory, SPDDocument, Employee, DocumentActivity


# ==================== EMPLOYEE SERIALIZER ====================

class EmployeeSerializer(serializers.ModelSerializer):
    """
    Serializer untuk Employee model (Master Data Pegawai)
    
    Menyediakan data pegawai untuk API endpoint /api/employees/
    
    Fields:
        - id: Primary key
        - nip: Nomor Induk Pegawai (18 digit)
        - name: Nama lengkap pegawai
        - position: Jabatan
        - department: Unit kerja
        - is_active: Status aktif (boolean)
    
    Usage:
        GET /api/employees/
        Response: [
            {
                "id": 1,
                "nip": "198501012010011001",
                "name": "John Doe",
                "position": "Staf Administrasi",
                "department": "Bagian Umum",
                "is_active": true
            }
        ]
    
    Implementasi Standar:
        - Read-only serializer (no create/update via API)
        - All fields included
        - Simple flat structure
    """
    
    class Meta:
        model = Employee
        fields = ['id', 'nip', 'name', 'position', 'department', 'is_active']


# ==================== CATEGORY SERIALIZER ====================

class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer untuk DocumentCategory model (Kategori Dokumen)
    
    Menyediakan data kategori dengan struktur hierarki dan counts.
    
    Fields:
        - id: Primary key
        - name: Nama kategori
        - slug: URL-safe identifier
        - parent: ID parent category (null untuk root)
        - parent_name: Nama parent category (computed)
        - icon: FontAwesome icon class
        - full_path: Full path hierarki (computed)
        - document_count: Jumlah dokumen aktif (computed)
    
    Computed Fields:
        - parent_name: Auto-resolved dari parent relation
        - full_path: Generated via get_full_path() method
        - document_count: Counted dari active documents only
    
    Usage:
        GET /api/categories/
        Response: [
            {
                "id": 1,
                "name": "Belanjaan",
                "slug": "belanjaan",
                "parent": null,
                "parent_name": null,
                "icon": "fa-shopping-cart",
                "full_path": "belanjaan",
                "document_count": 45
            },
            {
                "id": 2,
                "name": "ATK",
                "slug": "atk",
                "parent": 1,
                "parent_name": "Belanjaan",
                "icon": "fa-pencil",
                "full_path": "belanjaan/atk",
                "document_count": 12
            }
        ]
    
    Implementasi Standar:
        - Hierarki parent-child preserved
        - Counts hanya dokumen aktif (is_deleted=False)
        - Full path untuk folder structure
    """
    
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    full_path = serializers.SerializerMethodField()
    document_count = serializers.SerializerMethodField()
    
    class Meta:
        model = DocumentCategory
        fields = [
            'id', 'name', 'slug', 'parent', 'parent_name', 
            'icon', 'full_path', 'document_count'
        ]
    
    def get_full_path(self, obj):
        """
        Generate full hierarchical path untuk category
        
        Returns:
            str: Path seperti 'belanjaan/atk' atau 'spd'
        """
        return obj.get_full_path()
    
    def get_document_count(self, obj):
        """
        Hitung jumlah dokumen aktif di category ini
        
        Returns:
            int: Jumlah dokumen dengan is_deleted=False
        """
        return obj.documents.filter(is_deleted=False).count()


# ==================== SPD SERIALIZER ====================

class SPDSerializer(serializers.ModelSerializer):
    """
    Serializer untuk SPDDocument model (Surat Perjalanan Dinas)
    
    Menyediakan metadata lengkap SPD dengan employee dan destination info.
    
    Fields:
        - document: ID dokumen terkait
        - employee: ID pegawai
        - employee_name: Nama pegawai (computed)
        - employee_nip: NIP pegawai (computed)
        - destination: Kode tujuan
        - destination_display: Nama tujuan human-readable (computed)
        - destination_other: Tujuan lainnya (jika pilih 'other')
        - start_date: Tanggal mulai perjalanan
        - end_date: Tanggal selesai perjalanan
        - duration_days: Durasi dalam hari (computed)
        - created_at: Timestamp pembuatan
    
    Computed Fields:
        - employee_name: Dari employee.name relation
        - employee_nip: Dari employee.nip relation
        - destination_display: Handle 'other' dengan custom value
        - duration_days: Calculated dari start_date dan end_date
    
    Usage:
        GET /api/spd/
        Response: [
            {
                "document": 123,
                "employee": 5,
                "employee_name": "John Doe",
                "employee_nip": "198501012010011001",
                "destination": "jakarta",
                "destination_display": "Jakarta",
                "destination_other": null,
                "start_date": "2025-01-15",
                "end_date": "2025-01-17",
                "duration_days": 3,
                "created_at": "2025-01-10T10:30:00Z"
            }
        ]
    
    Implementasi Standar:
        - Nested employee info untuk convenience
        - Duration auto-calculated
        - Destination handling untuk 'other' case
    """
    
    employee_name = serializers.CharField(source='employee.name', read_only=True)
    employee_nip = serializers.CharField(source='employee.nip', read_only=True)
    destination_display = serializers.CharField(
        source='get_destination_display_full', 
        read_only=True
    )
    duration_days = serializers.IntegerField(
        source='get_duration_days', 
        read_only=True
    )
    
    class Meta:
        model = SPDDocument
        fields = [
            'document', 'employee', 'employee_name', 'employee_nip',
            'destination', 'destination_display', 'destination_other',
            'start_date', 'end_date', 'duration_days', 'created_at'
        ]


# ==================== DOCUMENT SERIALIZER ====================

class DocumentSerializer(serializers.ModelSerializer):
    """
    Serializer untuk Document model (Dokumen Utama)
    
    Menyediakan full document metadata dengan URLs untuk akses file,
    category info, user info, dan nested SPD info jika ada.
    
    Fields:
        Basic Info:
        - id: Primary key
        - display_name: Auto-generated name (computed)
        - file: File field (path)
        - file_url: Full URL untuk akses file (computed)
        - download_url: URL untuk download (computed)
        - preview_url: URL untuk preview (computed)
        - file_size: Ukuran dalam bytes
        - file_size_display: Human-readable size (computed)
        
        Dates:
        - document_date: Tanggal dokumen
        - document_date_formatted: Formatted date (computed)
        - created_at: Timestamp pembuatan
        - created_at_formatted: Formatted timestamp (computed)
        - updated_at: Timestamp update terakhir
        
        Relations:
        - category: ID kategori
        - category_name: Nama kategori (computed)
        - category_icon: Icon kategori (computed)
        - created_by: ID user pembuat
        - created_by_name: Nama user pembuat (computed)
        
        Metadata:
        - version: Version number
        - spd_info: Nested SPD data (jika dokumen SPD)
    
    Computed Fields:
        - display_name: Via get_filename() method
        - file_url: Absolute URL untuk file.url
        - download_url: Custom endpoint untuk download
        - preview_url: Custom endpoint untuk preview
        - file_size_display: Human-readable (KB, MB, GB)
        - document_date_formatted: Format Indonesia
        - created_at_formatted: Format Indonesia dengan waktu
        - category_name/icon: From category relation
        - created_by_name: From user relation
    
    Nested Serializers:
        - spd_info: Full SPDSerializer data (jika ada)
    
    Usage:
        GET /api/documents/123/
        Response: {
            "id": 123,
            "display_name": "SPD - John Doe - Jakarta (15 Januari 2025)",
            "file": "/media/uploads/spd/2025/01-Januari/SPD_JohnDoe_Jakarta.pdf",
            "file_url": "http://example.com/media/uploads/.../SPD_JohnDoe_Jakarta.pdf",
            "download_url": "http://example.com/api/documents/123/download/",
            "preview_url": "http://example.com/archive/documents/123/preview/",
            "file_size": 2048000,
            "file_size_display": "1.95 MB",
            "document_date": "2025-01-15",
            "document_date_formatted": "15 Januari 2025",
            "category": 5,
            "category_name": "SPD",
            "category_icon": "fa-plane",
            "created_by": 2,
            "created_by_name": "Admin User",
            "created_at": "2025-01-10T10:30:00Z",
            "created_at_formatted": "10 Januari 2025 10:30",
            "updated_at": "2025-01-10T10:30:00Z",
            "version": 1,
            "spd_info": {
                "employee": 5,
                "employee_name": "John Doe",
                "destination": "jakarta",
                "destination_display": "Jakarta",
                "start_date": "2025-01-15",
                "end_date": "2025-01-17",
                "duration_days": 3
            }
        }
    
    Implementasi Standar:
        - Comprehensive metadata untuk client apps
        - URLs siap pakai untuk file operations
        - Nested SPD info untuk convenience
        - Read-only (no create/update via this serializer)
        - Formatted dates untuk display
    """
    
    # Display name (computed dari metadata)
    display_name = serializers.CharField(source='get_filename', read_only=True)
    
    # Category info (nested)
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)
    
    # Created by info (nested)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    
    # File info (computed)
    file_size_display = serializers.CharField(
        source='get_file_size_display', 
        read_only=True
    )
    
    # URLs (computed via SerializerMethodField)
    file_url = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    preview_url = serializers.SerializerMethodField()
    
    # Date formatting (computed)
    document_date_formatted = serializers.SerializerMethodField()
    created_at_formatted = serializers.SerializerMethodField()
    
    # Nested SPD info (jika dokumen adalah SPD)
    spd_info = SPDSerializer(read_only=True)
    
    class Meta:
        model = Document
        fields = [
            'id', 'display_name', 
            'file', 'file_url', 'download_url', 'preview_url',
            'file_size', 'file_size_display', 
            'document_date', 'document_date_formatted', 
            'category', 'category_name', 'category_icon', 
            'created_by', 'created_by_name', 
            'created_at', 'created_at_formatted', 
            'updated_at', 'version', 
            'spd_info'
        ]
        read_only_fields = [
            'id', 'file_size', 'created_by', 
            'created_at', 'updated_at', 'version'
        ]
    
    def get_file_url(self, obj):
        """
        Generate absolute URL untuk file access
        
        Returns:
            str: Full URL seperti 'http://example.com/media/uploads/.../file.pdf'
            None: Jika file tidak ada
        """
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None
    
    def get_download_url(self, obj):
        """
        Generate URL untuk download endpoint
        
        Returns:
            str: API endpoint seperti '/api/documents/123/download/'
            None: Jika request context tidak ada
        """
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(f'/api/documents/{obj.id}/download/')
        return None
    
    def get_preview_url(self, obj):
        """
        Generate URL untuk preview endpoint
        
        Returns:
            str: Web endpoint seperti '/archive/documents/123/preview/'
            None: Jika request context tidak ada
        """
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(f'/archive/documents/{obj.id}/preview/')
        return None
    
    def get_document_date_formatted(self, obj):
        """
        Format document_date ke format Indonesia
        
        Returns:
            str: Format seperti '15 Januari 2025'
        """
        return obj.document_date.strftime('%d %B %Y')
    
    def get_created_at_formatted(self, obj):
        """
        Format created_at timestamp ke format Indonesia dengan waktu
        
        Returns:
            str: Format seperti '10 Januari 2025 10:30'
        """
        return obj.created_at.strftime('%d %B %Y %H:%M')


# ==================== DOCUMENT ACTIVITY SERIALIZER ====================

class DocumentActivitySerializer(serializers.ModelSerializer):
    """
    Serializer untuk DocumentActivity model (Audit Trail)
    
    Menyediakan log aktivitas dokumen dengan user info dan timestamps.
    
    Fields:
        - id: Primary key
        - document: ID dokumen terkait
        - user: ID user yang melakukan aksi
        - user_name: Nama user (computed)
        - action_type: Tipe aksi (create, view, download, update, delete)
        - action_display: Label action human-readable (computed)
        - description: Deskripsi detail (optional)
        - ip_address: IP address user
        - created_at: Timestamp aksi
        - created_at_formatted: Formatted timestamp (computed)
        - time_ago: Relative time (computed)
    
    Computed Fields:
        - user_name: Dari user.full_name relation
        - action_display: Dari get_action_type_display() choices
        - created_at_formatted: Format Indonesia
        - time_ago: Human-readable relative time ('2 jam yang lalu')
    
    Usage:
        GET /api/documents/123/activities/
        Response: [
            {
                "id": 456,
                "document": 123,
                "user": 2,
                "user_name": "Admin User",
                "action_type": "download",
                "action_display": "Mengunduh",
                "description": "Downloaded via web interface",
                "ip_address": "192.168.1.100",
                "created_at": "2025-01-15T14:30:00Z",
                "created_at_formatted": "15 Januari 2025 14:30",
                "time_ago": "2 jam yang lalu"
            }
        ]
    
    Implementasi Standar:
        - Read-only (activities auto-generated)
        - Comprehensive audit info
        - Human-readable timestamps
        - IP tracking untuk security
    """
    
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    action_display = serializers.CharField(
        source='get_action_type_display', 
        read_only=True
    )
    created_at_formatted = serializers.SerializerMethodField()
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = DocumentActivity
        fields = [
            'id', 'document', 'user', 'user_name', 
            'action_type', 'action_display', 'description', 
            'ip_address', 'created_at', 'created_at_formatted', 
            'time_ago'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_created_at_formatted(self, obj):
        """
        Format timestamp ke format Indonesia dengan waktu
        
        Returns:
            str: Format seperti '15 Januari 2025 14:30'
        """
        return obj.created_at.strftime('%d %B %Y %H:%M')
    
    def get_time_ago(self, obj):
        """
        Calculate relative time dari created_at ke sekarang
        
        Menghasilkan human-readable relative time seperti:
        - 'Baru saja' (< 1 menit)
        - '5 menit yang lalu'
        - '2 jam yang lalu'
        - '3 hari yang lalu'
        - '2 minggu yang lalu'
        - Atau tanggal lengkap jika > 1 bulan
        
        Returns:
            str: Relative time dalam Bahasa Indonesia
        """
        from django.utils import timezone
        
        now = timezone.now()
        diff = now - obj.created_at
        seconds = diff.total_seconds()
        
        # Kurang dari 1 menit
        if seconds < 60:
            return 'Baru saja'
        
        # Kurang dari 1 jam
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f'{minutes} menit yang lalu'
        
        # Kurang dari 1 hari
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f'{hours} jam yang lalu'
        
        # Kurang dari 1 minggu
        elif seconds < 604800:
            days = int(seconds / 86400)
            return f'{days} hari yang lalu'
        
        # Kurang dari 1 bulan
        elif seconds < 2592000:
            weeks = int(seconds / 604800)
            return f'{weeks} minggu yang lalu'
        
        # Lebih dari 1 bulan: tampilkan tanggal lengkap
        else:
            return obj.created_at.strftime('%d %B %Y')