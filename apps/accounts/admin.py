"""
Modul: apps/accounts/admin.py
Fungsi: Django Admin configuration untuk User model

Berisi:
    - UserAdmin: Custom admin untuk User model
    - Improved list display dengan filters
    - Search functionality
    - Inline group display
    - Custom actions

Implementasi Standar:
    - Menggunakan CustomUserChangeForm untuk konsistensi
    - List filters untuk easy navigation
    - Search fields untuk quick find
    - Readonly fields untuk audit
    - Custom actions untuk bulk operations

Catatan Pemeliharaan:
    - Admin interface untuk superuser only
    - Tidak expose password field (security)
    - Show created_at dan updated_at untuk audit
    - Group dan permission management integrated
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import User
from .forms import CustomUserChangeForm


class UserAdmin(BaseUserAdmin):
    """
    Custom User Admin dengan enhanced features
    
    Features:
        - Custom list display dengan status badges
        - Search by username, full_name, email
        - Filter by staff status, active status, groups
        - Readonly audit fields (date_joined, last_login)
        - Inline group display
        - Custom actions (activate, deactivate)
    
    Implementasi Standar:
        - Consistent dengan Django best practices
        - User-friendly interface
        - Security focused (no password exposure)
    """
    
    # Use custom form
    form = CustomUserChangeForm
    
    # List display
    list_display = (
        'username',
        'full_name_display',
        'email',
        'phone',
        'status_badges',
        'groups_display',
        'document_count',
        'date_joined_short',
        'last_login_short'
    )
    
    # List filters
    list_filter = (
        'is_active',
        'is_staff',
        'is_superuser',
        'groups',
        'date_joined',
    )
    
    # Search fields
    search_fields = (
        'username',
        'full_name',
        'email',
        'phone'
    )
    
    # Ordering
    ordering = ('-date_joined',)
    
    # Readonly fields (untuk audit)
    readonly_fields = (
        'date_joined',
        'last_login',
        'created_at',
        'updated_at'
    )
    
    # Fieldsets untuk detail page
    fieldsets = (
        ('Login Info', {
            'fields': ('username', 'password')
        }),
        ('Personal Info', {
            'fields': ('full_name', 'email', 'phone')
        }),
        ('Permissions', {
            'fields': (
                'is_active',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions'
            ),
            'classes': ('collapse',)
        }),
        ('Important Dates', {
            'fields': (
                'last_login',
                'date_joined',
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    # Add fieldsets (untuk create user)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username',
                'password1',
                'password2',
                'full_name',
                'email',
                'phone',
                'is_active',
                'is_staff',
                'is_superuser',
                'groups'
            ),
        }),
    )
    
    # Custom display methods
    
    def full_name_display(self, obj):
        """Display full name dengan fallback ke username"""
        return obj.full_name or obj.username
    full_name_display.short_description = 'Nama Lengkap' # type: ignore
    full_name_display.admin_order_field = 'full_name' # type: ignore
    
    def status_badges(self, obj):
        """Display status badges (Active, Staff, Superuser)"""
        badges = []
        
        if obj.is_active:
            badges.append(
                '<span style="background-color: #28a745; color: white; '
                'padding: 3px 8px; border-radius: 3px; font-size: 11px;">'
                'Active</span>'
            )
        else:
            badges.append(
                '<span style="background-color: #dc3545; color: white; '
                'padding: 3px 8px; border-radius: 3px; font-size: 11px;">'
                'Inactive</span>'
            )
        
        if obj.is_superuser:
            badges.append(
                '<span style="background-color: #dc3545; color: white; '
                'padding: 3px 8px; border-radius: 3px; font-size: 11px;">'
                'Superuser</span>'
            )
        elif obj.is_staff:
            badges.append(
                '<span style="background-color: #ffc107; color: white; '
                'padding: 3px 8px; border-radius: 3px; font-size: 11px;">'
                'Staff</span>'
            )
        
        return mark_safe(' '.join(badges))
    status_badges.short_description = 'Status' # type: ignore
    
    def groups_display(self, obj):
        """Display groups sebagai comma-separated list"""
        groups = obj.groups.all()
        if groups:
            group_names = [g.name for g in groups]
            return ', '.join(group_names)
        return '-'
    groups_display.short_description = 'Groups' # type: ignore
    
    def document_count(self, obj):
        """Display jumlah dokumen yang diupload"""
        count = obj.documents_created.filter(is_deleted=False).count()
        if count > 0:
            url = reverse('admin:archive_document_changelist') + f'?created_by__id__exact={obj.id}'
            return format_html(
                '<a href="{}">{} docs</a>',
                url,
                count
            )
        return '0'
    document_count.short_description = 'Documents' # type: ignore
    
    def date_joined_short(self, obj):
        """Display date joined dengan format short"""
        if obj.date_joined:
            return obj.date_joined.strftime('%d/%m/%Y')
        return '-'
    date_joined_short.short_description = 'Joined' # type: ignore
    date_joined_short.admin_order_field = 'date_joined' # type: ignore
    
    def last_login_short(self, obj):
        """Display last login dengan format short"""
        if obj.last_login:
            return obj.last_login.strftime('%d/%m/%Y %H:%M')
        return 'Never'
    last_login_short.short_description = 'Last Login' # type: ignore
    last_login_short.admin_order_field = 'last_login' # type: ignore
    
    # Custom actions
    
    def activate_users(self, request, queryset):
        """Bulk action: Activate selected users"""
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f'{updated} user(s) berhasil diaktifkan.'
        )
    activate_users.short_description = 'Aktifkan user yang dipilih' # type: ignore
    
    def deactivate_users(self, request, queryset):
        """Bulk action: Deactivate selected users"""
        # Prevent deactivating own account
        if request.user in queryset:
            self.message_user(
                request,
                'Tidak dapat menonaktifkan akun sendiri.',
                level='error'
            )
            return
        
        updated = queryset.exclude(pk=request.user.pk).update(is_active=False)
        self.message_user(
            request,
            f'{updated} user(s) berhasil dinonaktifkan.'
        )
    deactivate_users.short_description = 'Nonaktifkan user yang dipilih' # type: ignore
    
    def make_staff(self, request, queryset):
        """Bulk action: Make users staff"""
        updated = queryset.update(is_staff=True)
        self.message_user(
            request,
            f'{updated} user(s) dijadikan staff.'
        )
    make_staff.short_description = 'Jadikan staff' # type: ignore
    
    def remove_staff(self, request, queryset):
        """Bulk action: Remove staff status"""
        # Prevent removing own staff status
        if request.user in queryset:
            self.message_user(
                request,
                'Tidak dapat menghapus status staff sendiri.',
                level='error'
            )
            return
        
        updated = queryset.exclude(pk=request.user.pk).update(is_staff=False)
        self.message_user(
            request,
            f'{updated} user(s) tidak lagi staff.'
        )
    remove_staff.short_description = 'Hapus status staff' # type: ignore
    
    # Register actions
    actions = [
        'activate_users',
        'deactivate_users',
        'make_staff',
        'remove_staff'
    ]
    
    # Permissions
    
    def has_delete_permission(self, request, obj=None):
        """
        Prevent hard delete dari admin
        Gunakan deactivate instead
        """
        # Superuser bisa hard delete jika perlu
        return request.user.is_superuser # type: ignore
    
    def get_queryset(self, request):
        """
        Optimize queryset dengan prefetch groups
        """
        qs = super().get_queryset(request)
        qs = qs.prefetch_related('groups')
        return qs


# Register User model
admin.site.register(User, UserAdmin)

# Customize admin site header
admin.site.site_header = 'Sistem Arsip Digital - Admin'
admin.site.site_title = 'Arsip Digital Admin'
admin.site.index_title = 'Dashboard Admin'