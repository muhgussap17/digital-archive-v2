from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from .models import (
    User, Employee, DocumentCategory, Document, 
    SPDDocument, DocumentActivity, SystemSetting
)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Admin for User model"""
    list_display = ['username', 'full_name', 'email', 'is_staff', 'is_active', 'created_at']
    list_filter = ['is_staff', 'is_active', 'created_at']
    search_fields = ['username', 'full_name', 'email']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Informasi Login', {
            'fields': ('username', 'password')
        }),
        ('Informasi Personal', {
            'fields': ('full_name', 'email', 'phone')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Tanggal Penting', {
            'fields': ('last_login', 'date_joined')
        }),
    )
    
    readonly_fields = ['last_login', 'date_joined']


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    """Admin for Employee model"""
    list_display = ['nip', 'name', 'position', 'department', 'is_active', 'spd_count']
    list_filter = ['is_active', 'department', 'position']
    search_fields = ['nip', 'name', 'position', 'department']
    ordering = ['name']
    
    fieldsets = (
        ('Data Pegawai', {
            'fields': ('nip', 'name', 'position', 'department')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    def spd_count(self, obj):
        """Count SPD documents"""
        count = obj.spd_documents.filter(document__is_deleted=False).count()
        if count > 0:
            url = reverse('admin:archive_spddocument_changelist') + f'?employee__id__exact={obj.id}'
            return format_html('<a href="{}">{} SPD</a>', url, count)
        return '0 SPD'
    
    spd_count.short_description = 'Jumlah SPD' # pyright: ignore[reportFunctionMemberAccess]


@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    """Admin for DocumentCategory model"""
    list_display = ['name', 'slug', 'parent', 'icon_preview', 'document_count']
    list_filter = ['parent']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['parent__name', 'name']
    
    fieldsets = (
        ('Informasi Kategori', {
            'fields': ('name', 'slug', 'parent')
        }),
        ('Tampilan', {
            'fields': ('icon',),
            'description': 'Gunakan class FontAwesome, contoh: fa-plane, fa-shopping-cart'
        }),
    )
    
    def icon_preview(self, obj):
        """Show icon preview"""
        return format_html('<i class="fa-solid {}"></i> {}', obj.icon, obj.icon)
    
    icon_preview.short_description = 'Icon' # pyright: ignore[reportFunctionMemberAccess]
    
    def document_count(self, obj):
        """Count documents"""
        count = obj.documents.filter(is_deleted=False).count()
        if count > 0:
            url = reverse('admin:archive_document_changelist') + f'?category__id__exact={obj.id}'
            return format_html('<a href="{}">{} dokumen</a>', url, count)
        return '0 dokumen'
    
    document_count.short_description = 'Jumlah Dokumen' # pyright: ignore[reportFunctionMemberAccess]


class SPDDocumentInline(admin.StackedInline):
    """Inline for SPD Document"""
    model = SPDDocument
    extra = 0
    fields = ['employee', 'destination', 'destination_other', 'start_date', 'end_date']
    
    def has_add_permission(self, request, obj=None):
        # Only allow if document category is SPD
        if obj and obj.category.slug != 'spd':
            return False
        return super().has_add_permission(request, obj) # pyright: ignore[reportCallIssue]


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Admin for Document model"""
    list_display = [
        'display_name_column', 'category', 'document_date', 'file_size_display',
        'created_by', 'created_at', 'status_badge'
    ]
    list_filter = ['category', 'document_date', 'created_at', 'is_deleted']
    search_fields = ['created_by__full_name', 'spd_info__employee__name']
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
        """Display auto-generated name"""
        return obj.get_display_name()
    
    display_name_column.short_description = 'Nama Dokumen' # type: ignore

    def file_size_display(self, obj):
        """Display file size"""
        return obj.get_file_size_display()
    
    file_size_display.short_description = 'Ukuran File' # pyright: ignore[reportFunctionMemberAccess]
    
    def status_badge(self, obj):
        """Display status badge"""
        if obj.is_deleted:
            return format_html(
                '<span style="color: red; font-weight: bold;">● Dihapus</span>'
            )
        return format_html(
            '<span style="color: green; font-weight: bold;">● Aktif</span>'
        )
    
    status_badge.short_description = 'Status' # pyright: ignore[reportFunctionMemberAccess]
    
    def get_queryset(self, request):
        """Include deleted documents in admin"""
        qs = super().get_queryset(request)
        return qs.select_related('category', 'created_by')
    
    actions = ['restore_documents']
    
    def restore_documents(self, request, queryset):
        """Restore soft-deleted documents"""
        count = queryset.filter(is_deleted=True).update(
            is_deleted=False,
            deleted_at=None
        )
        self.message_user(request, f'{count} dokumen berhasil dipulihkan.')
    
    restore_documents.short_description = 'Pulihkan dokumen yang dipilih' # pyright: ignore[reportFunctionMemberAccess]


@admin.register(SPDDocument)
class SPDDocumentAdmin(admin.ModelAdmin):
    """Admin for SPD Document"""
    list_display = [
        'document_title', 'employee', 'destination_display',
        'start_date', 'end_date', 'duration', 'created_at'
    ]
    list_filter = ['destination', 'start_date', 'created_at']
    search_fields = [
        'document__title', 'employee__name', 'employee__nip',
        'destination', 'destination_other'
    ]
    date_hierarchy = 'start_date'
    ordering = ['-start_date']
    readonly_fields = ['created_at', 'duration']
    
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
                'start_date', 'end_date'
            )
        }),
        ('Timestamp', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def document_title(self, obj):
        """Get document title"""
        url = reverse('admin:archive_document_change', args=[obj.document.id])
        return format_html('<a href="{}">{}</a>', url, obj.document.file)
    
    document_title.short_description = 'Dokumen' # pyright: ignore[reportFunctionMemberAccess]
    
    def destination_display(self, obj):
        """Display destination"""
        return obj.get_destination_display_full()
    
    destination_display.short_description = 'Tujuan' # pyright: ignore[reportFunctionMemberAccess]
    
    def duration(self, obj):
        """Display trip duration"""
        days = obj.get_duration_days()
        return f'{days} hari'
    
    duration.short_description = 'Durasi' # pyright: ignore[reportFunctionMemberAccess]
    
    def get_queryset(self, request):
        """Optimize queries"""
        qs = super().get_queryset(request)
        return qs.select_related('document', 'employee')


@admin.register(DocumentActivity)
class DocumentActivityAdmin(admin.ModelAdmin):
    """Admin for Document Activity"""
    list_display = [
        'document_title', 'action_badge', 'user_name',
        'ip_address', 'created_at'
    ]
    list_filter = ['action_type', 'created_at']
    search_fields = ['document__title', 'user__full_name', 'description', 'ip_address']
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
        """Get document title with link"""
        if obj.document:
            url = reverse('admin:archive_document_change', args=[obj.document.id])
            return format_html('<a href="{}">{}</a>', url, obj.document.file)
        return '-'
    
    document_title.short_description = 'Dokumen' # type: ignore
    
    def user_name(self, obj):
        """Get user name"""
        return obj.user.full_name if obj.user else '-'
    
    user_name.short_description = 'User' # type: ignore
    
    def action_badge(self, obj):
        """Display action with color badge"""
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
    
    def get_queryset(self, request):
        """Optimize queries"""
        qs = super().get_queryset(request)
        return qs.select_related('document', 'user')
    
    def has_add_permission(self, request):
        """Disable manual creation of activities"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable editing of activities"""
        return False


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    """Admin for System Settings"""
    list_display = ['key', 'value_preview', 'updated_at', 'updated_by']
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
        """Show preview of value"""
        if len(obj.value) > 50:
            return f'{obj.value[:50]}...'
        return obj.value
    
    value_preview.short_description = 'Value' # type: ignore
    
    def save_model(self, request, obj, form, change):
        """Set updated_by automatically"""
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


# Customize Admin Site
admin.site.site_header = 'Sistem Arsip Digital'
admin.site.site_title = 'Admin Arsip Digital'
admin.site.index_title = 'Dashboard Administrasi'