"""
Modul: apps/archive/admin.py (REFACTORED)
Fungsi: Django Admin configuration untuk Archive models

Berisi admin classes untuk:
    - Employee: Master data pegawai
    - DocumentCategory: Kategori dokumen hierarki
    - Document: Dokumen utama dengan SPD inline
    - SPDDocument: Metadata SPD
    - DocumentActivity: Audit trail aktivitas
    - SystemSetting: Pengaturan sistem

Implementasi Standar:
    - Enhanced list display dengan badges dan links
    - Search dan filter optimization
    - Query optimization dengan select_related
    - Custom actions untuk bulk operations
    - Readonly fields untuk audit
    - Security: disable manual activity creation

Catatan Pemeliharaan:
    - Document.title TIDAK ADA, gunakan get_file_name()
    - Semua admin menggunakan query optimization
    - Activity logging read-only (auto-generated)
    - Soft delete restoration via bulk action
    
Bug Fixes:
    - Fixed: 'Document' object has no attribute 'title'
    - Changed all document.title to document.get_file_name()
    - Fixed SPDDocumentAdmin.document_title method
    - Fixed DocumentActivityAdmin.document_title method
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Q
from django.utils.safestring import mark_safe

from .models import (
    Employee, DocumentCategory, Document, 
    SPDDocument, DocumentActivity, SystemSetting
)


# ==================== EMPLOYEE ADMIN ====================

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    """
    Admin interface untuk Employee model
    
    Features:
        - List display dengan SPD count
        - Filter by active status, department, position
        - Search by NIP, name, position, department
        - Fieldsets organization
        - SPD count dengan link ke SPD list
    
    Optimization:
        - No additional queries needed (count done in method)
    
    Implementasi Standar:
        - Readonly created_at, updated_at
        - Clear fieldset organization
    """
    
    list_display = [
        'nip', 'name', 'position', 'department', 
        'status_badge', 'spd_count', 'created_at_short'
    ]
    list_filter = ['is_active', 'department', 'position', 'created_at']
    search_fields = ['nip', 'name', 'position', 'department']
    ordering = ['name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Data Pegawai', {
            'fields': ('nip', 'name', 'position', 'department')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamp', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        """Display status badge dengan warna"""
        if obj.is_active:
            return format_html(
                '<span style="color: green; font-weight: bold;">● Aktif</span>'
            )
        return format_html(
            '<span style="color: red; font-weight: bold;">● Nonaktif</span>'
        )
    status_badge.short_description = 'Status' # type: ignore
    
    def spd_count(self, obj):
        """Count SPD documents dengan link ke filtered list"""
        count = obj.spd_documents.filter(document__is_deleted=False).count()
        if count > 0:
            url = reverse('admin:archive_spddocument_changelist') + f'?employee__id__exact={obj.id}'
            return format_html('<a href="{}">{} SPD</a>', url, count)
        return '0 SPD'
    spd_count.short_description = 'Jumlah SPD' # type: ignore
    
    def created_at_short(self, obj):
        """Display created_at dengan format short"""
        if obj.created_at:
            return obj.created_at.strftime('%d/%m/%Y')
        return '-'
    created_at_short.short_description = 'Dibuat' # type: ignore
    created_at_short.admin_order_field = 'created_at' # type: ignore


# ==================== DOCUMENT CATEGORY ADMIN ====================

@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    """
    Admin interface untuk DocumentCategory model
    
    Features:
        - Hierarchical display (parent-child)
        - Icon preview dengan FontAwesome
        - Document count dengan link
        - Auto-generate slug dari name
    
    Optimization:
        - Query optimization di get_queryset
    
    Implementasi Standar:
        - Prepopulated slug field
        - Icon helper text
        - Document count dengan filter link
    """
    
    list_display = [
        'name', 'slug', 'parent', 'icon_preview', 
        'document_count', 'created_at_short'
    ]
    list_filter = ['parent', 'created_at']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['parent__name', 'name']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Informasi Kategori', {
            'fields': ('name', 'slug', 'parent')
        }),
        ('Tampilan', {
            'fields': ('icon',),
            'description': 'Gunakan class FontAwesome, contoh: fa-plane, fa-shopping-cart'
        }),
        ('Timestamp', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def icon_preview(self, obj):
        """Show icon preview dengan FontAwesome"""
        return format_html('<i class="fa-solid {}"></i> {}', obj.icon, obj.icon)
    icon_preview.short_description = 'Icon' # type: ignore
    
    def document_count(self, obj):
        """Count documents dengan link ke filtered list"""
        count = obj.documents.filter(is_deleted=False).count()
        if count > 0:
            url = reverse('admin:archive_document_changelist') + f'?category__id__exact={obj.id}'
            return format_html('<a href="{}">{} dokumen</a>', url, count)
        return '0 dokumen'
    document_count.short_description = 'Jumlah Dokumen' # type: ignore
    
    def created_at_short(self, obj):
        """Display created_at dengan format short"""
        if obj.created_at:
            return obj.created_at.strftime('%d/%m/%Y')
        return '-'
    created_at_short.short_description = 'Dibuat' # type: ignore
    created_at_short.admin_order_field = 'created_at' # type: ignore


# ==================== SPD DOCUMENT INLINE ====================

class SPDDocumentInline(admin.StackedInline):
    """
    Inline admin untuk SPDDocument di Document admin
    
    Features:
        - Stacked layout untuk better readability
        - Conditional display (only for SPD category)
        - All SPD fields editable
    
    Security:
        - Only allow add if document category is SPD
    
    Implementasi Standar:
        - Clean inline interface
        - Validation handled by model
    """
    
    model = SPDDocument
    extra = 0
    fields = ['employee', 'destination', 'destination_other', 'start_date', 'end_date']
    
    def has_add_permission(self, request, obj=None):
        """Only allow if document category is SPD"""
        if obj and obj.category.slug != 'spd':
            return False
        return super().has_add_permission(request, obj)


# ==================== DOCUMENT ADMIN ====================

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """
    Admin interface untuk Document model
    
    Features:
        - Display name dari get_filename()
        - File size human readable
        - Status badge (active/deleted)
        - SPD inline untuk kategori SPD
        - Restore action untuk soft-deleted documents
    
    Optimization:
        - select_related di get_queryset
        - Efficient filtering
    
    Implementasi Standar:
        - Readonly metadata fields
        - Date hierarchy untuk easy navigation
        - Bulk restore action
    """
    
    list_display = [
        'display_name_column', 'category', 'document_date', 
        'file_size_display', 'created_by', 'created_at_short', 
        'status_badge'
    ]
    list_filter = ['category', 'document_date', 'created_at', 'is_deleted']
    search_fields = ['created_by__username', 'created_by__full_name', 'spd_info__employee__name']
    date_hierarchy = 'document_date'
    ordering = ['-document_date', '-created_at']
    readonly_fields = ['file_size', 'version', 'created_at', 'updated_at', 'deleted_at']
    inlines = [SPDDocumentInline]
    
    fieldsets = (
        ('Informasi Dokumen', {
            'fields': ('category', 'document_date', 'file')
        }),
        ('Metadata', {
            'fields': ('file_size', 'version', 'created_by')
        }),
        ('Status', {
            'fields': ('is_deleted', 'deleted_at')
        }),
        ('Timestamp', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def display_name_column(self, obj):
        """
        Display auto-generated name dari get_filename()
        
        FIXED: Tidak lagi menggunakan document.title (tidak ada)
        """
        return obj.get_filename()
    display_name_column.short_description = 'Nama Dokumen' # type: ignore

    def file_size_display(self, obj):
        """Display file size dalam format human readable"""
        return obj.get_file_size_display()
    file_size_display.short_description = 'Ukuran File' # type: ignore
    
    def created_at_short(self, obj):
        """Display created_at dengan format short"""
        return obj.created_at.strftime('%d/%m/%Y %H:%M')
    created_at_short.short_description = 'Dibuat' # type: ignore
    created_at_short.admin_order_field = 'created_at' # type: ignore
    
    def status_badge(self, obj):
        """Display status badge dengan warna"""
        if obj.is_deleted:
            return format_html(
                '<span style="color: red; font-weight: bold;">● Dihapus</span>'
            )
        return format_html(
            '<span style="color: green; font-weight: bold;">● Aktif</span>'
        )
    status_badge.short_description = 'Status' # type: ignore
    
    def get_queryset(self, request):
        """
        Include deleted documents in admin
        Optimize dengan select_related
        """
        qs = super().get_queryset(request)
        return qs.select_related('category', 'created_by')
    
    # Custom actions
    actions = ['restore_documents']
    
    def restore_documents(self, request, queryset):
        """
        Bulk action: Restore soft-deleted documents
        
        Sets is_deleted=False dan cleared deleted_at timestamp
        """
        count = queryset.filter(is_deleted=True).update(
            is_deleted=False,
            deleted_at=None
        )
        self.message_user(request, f'{count} dokumen berhasil dipulihkan.')
    restore_documents.short_description = 'Pulihkan dokumen yang dipilih' # type: ignore


# ==================== SPD DOCUMENT ADMIN ====================

@admin.register(SPDDocument)
class SPDDocumentAdmin(admin.ModelAdmin):
    """
    Admin interface untuk SPDDocument model
    
    Features:
        - Display document name dengan link
        - Destination display (handle 'other')
        - Duration calculation
        - Employee info
    
    Optimization:
        - select_related di get_queryset
        - Efficient foreign key queries
    
    Implementasi Standar:
        - Readonly calculated fields (duration)
        - Date hierarchy untuk easy navigation
        - Clear fieldsets organization
    """
    
    list_display = [
        'document_title', 'employee', 'destination_display',
        'start_date', 'end_date', 'duration', 'created_at_short'
    ]
    list_filter = ['destination', 'start_date', 'created_at', 'employee']
    search_fields = [
        'employee__name', 'employee__nip',
        'destination', 'destination_other'
    ]
    date_hierarchy = 'start_date'
    ordering = ['-start_date']
    readonly_fields = ['created_at', 'duration_display']
    
    fieldsets = (
        ('Dokumen', {
            'fields': ('document',)
        }),
        ('Informasi Pegawai', {
            'fields': ('employee',)
        }),
        ('Detail Perjalanan', {
            'fields': (
                'destination', 'destination_other',
                'start_date', 'end_date', 'duration_display'
            )
        }),
        ('Timestamp', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def document_title(self, obj):
        """
        Get document display name dengan link ke document admin
        
        FIXED: Menggunakan get_filename() bukan title
        """
        url = reverse('admin:archive_document_change', args=[obj.document.id])
        display_name = obj.document.get_filename()
        return format_html('<a href="{}">{}</a>', url, display_name)
    document_title.short_description = 'Dokumen' # type: ignore
    
    def destination_display(self, obj):
        """Display destination (handle 'other' dengan custom value)"""
        return obj.get_destination_display_full()
    destination_display.short_description = 'Tujuan' # type: ignore
    
    def duration(self, obj):
        """Display trip duration dalam hari"""
        days = obj.get_duration_days()
        return f'{days} hari'
    duration.short_description = 'Durasi' # type: ignore
    
    def duration_display(self, obj):
        """Readonly field untuk duration di detail page"""
        days = obj.get_duration_days()
        return f'{days} hari'
    duration_display.short_description = 'Durasi Perjalanan' # type: ignore
    
    def created_at_short(self, obj):
        """Display created_at dengan format short"""
        return obj.created_at.strftime('%d/%m/%Y')
    created_at_short.short_description = 'Dibuat' # type: ignore
    created_at_short.admin_order_field = 'created_at' # type: ignore
    
    def get_queryset(self, request):
        """Optimize queries dengan select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('document', 'document__category', 'employee')


# ==================== DOCUMENT ACTIVITY ADMIN ====================

@admin.register(DocumentActivity)
class DocumentActivityAdmin(admin.ModelAdmin):
    """
    Admin interface untuk DocumentActivity model
    
    Features:
        - Audit trail display
        - Action badges dengan warna
        - User dan IP tracking
        - Document link
    
    Security:
        - Read-only (no add/change)
        - Automatic logging only
    
    Optimization:
        - select_related di get_queryset
    
    Implementasi Standar:
        - Readonly interface (audit trail)
        - Comprehensive filtering
        - Date hierarchy
    """
    
    list_display = [
        'document_title', 'action_badge', 'user_name',
        'ip_address', 'created_at_short'
    ]
    list_filter = ['action_type', 'created_at', 'user']
    search_fields = [
        'user__username', 'user__full_name', 
        'description', 'ip_address'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Aktivitas', {
            'fields': ('document', 'user', 'action_type', 'description')
        }),
        ('Detail Teknis', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )
    
    def document_title(self, obj):
        """
        Get document display name dengan link
        
        FIXED: Menggunakan get_filename() bukan title
        """
        if obj.document:
            url = reverse('admin:archive_document_change', args=[obj.document.id])
            display_name = obj.document.get_filename()
            return format_html('<a href="{}">{}</a>', url, display_name)
        return '-'
    document_title.short_description = 'Dokumen' # type: ignore
    
    def user_name(self, obj):
        """Get user full name atau username"""
        if obj.user:
            return obj.user.full_name or obj.user.username
        return '-'
    user_name.short_description = 'User' # type: ignore
    
    def action_badge(self, obj):
        """Display action dengan color badge"""
        colors = {
            'create': 'green',
            'view': 'blue',
            'download': 'orange',
            'update': 'purple',
            'delete': 'red',
        }
        color = colors.get(obj.action_type, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">● {}</span>',
            color,
            obj.get_action_type_display()
        )
    action_badge.short_description = 'Aksi' # type: ignore
    
    def created_at_short(self, obj):
        """Display created_at dengan format short"""
        return obj.created_at.strftime('%d/%m/%Y %H:%M')
    created_at_short.short_description = 'Waktu' # type: ignore
    created_at_short.admin_order_field = 'created_at' # type: ignore
    
    def get_queryset(self, request):
        """Optimize queries dengan select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('document', 'document__category', 'user')
    
    def has_add_permission(self, request):
        """Disable manual creation of activities (auto-generated only)"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable editing of activities (audit trail immutable)"""
        return False


# ==================== SYSTEM SETTING ADMIN ====================

@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    """
    Admin interface untuk SystemSetting model
    
    Features:
        - Key-value configuration
        - Value preview (truncate long values)
        - Auto-set updated_by
    
    Security:
        - updated_by automatically set on save
    
    Implementasi Standar:
        - Clear fieldsets
        - Readonly updated_at
        - Automatic metadata tracking
    """
    
    list_display = ['key', 'value_preview', 'updated_at_short', 'updated_by']
    search_fields = ['key', 'value', 'description']
    ordering = ['key']
    readonly_fields = ['updated_at']
    
    fieldsets = (
        ('Setting', {
            'fields': ('key', 'value', 'description')
        }),
        ('Metadata', {
            'fields': ('updated_at', 'updated_by')
        }),
    )
    
    def value_preview(self, obj):
        """Show preview of value (truncate jika panjang)"""
        if len(obj.value) > 50:
            return f'{obj.value[:50]}...'
        return obj.value
    value_preview.short_description = 'Value' # type: ignore
    
    def updated_at_short(self, obj):
        """Display updated_at dengan format short"""
        return obj.updated_at.strftime('%d/%m/%Y %H:%M')
    updated_at_short.short_description = 'Terakhir Diubah' # type: ignore
    updated_at_short.admin_order_field = 'updated_at' # type: ignore
    
    def save_model(self, request, obj, form, change):
        """Set updated_by automatically ke user yang melakukan update"""
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


# ==================== ADMIN SITE CUSTOMIZATION ====================

# Customize Admin Site headers
admin.site.site_header = 'Sistem Arsip Digital - Admin'
admin.site.site_title = 'Admin Arsip Digital'
admin.site.index_title = 'Dashboard Administrasi'