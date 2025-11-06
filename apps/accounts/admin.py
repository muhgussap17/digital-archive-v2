from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User
from .forms import CustomUserChangeForm

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Mendaftarkan Model User Kustom ke panel admin
    """
    # Gunakan form kustom yang kita buat
    form = CustomUserChangeForm
    
    # list_display = ('username', 'email', 'full_name', 'phone', 'is_staff', 'is_active')
    list_display = ['username', 'full_name', 'email', 'phone', 'is_staff', 'is_active', 'created_at']
    # list_filter = ('is_staff', 'is_active', 'groups')
    list_filter = ['is_staff', 'is_active', 'created_at', 'groups']
    # search_fields = ('username', 'full_name', 'email', 'phone')
    search_fields = ['username', 'full_name', 'email', 'phone']
    ordering = ['-created_at']

    # Atur fieldsets untuk halaman edit user di admin
    # Ini menambahkan 'Data Pribadi' ke halaman admin
    fieldsets = UserAdmin.fieldsets + (
        ('Data Pribadi', {'fields': ('full_name', 'phone')}),
    ) # type: ignore
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Data Pribadi', {'fields': ('full_name', 'phone')}),
    )

    # list_display = ['username', 'full_name', 'email', 'phone', 'is_staff', 'is_active', 'created_at']
    # list_filter = ['is_staff', 'is_active', 'created_at', 'groups']
    # search_fields = ['username', 'full_name', 'email', 'phone']
    # ordering = ['-created_at']
    
    # fieldsets = UserAdmin.fieldsets + (
    #     ('Informasi Login', {
    #         'fields': ('username', 'password')
    #     }),
    #     ('Informasi Personal', {
    #         'fields': ('full_name', 'email', 'phone')
    #     }),
    #     ('Permissions', {
    #         'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
    #     }),
    #     ('Tanggal Penting', {
    #         'fields': ('last_login', 'date_joined')
    #     }),
    # ) # type: ignore
    
    # readonly_fields = ['last_login', 'date_joined']