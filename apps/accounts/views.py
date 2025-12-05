"""
Modul: apps/accounts/views.py (REFACTORED)
Fungsi: Views untuk User management (profile + CRUD)

Views:
    PROFILE (existing, improved):
    - profile: User profile dashboard
    - profile_edit: Edit own profile
    
    USER MANAGEMENT (new):
    - user_list: List users dengan filter & search
    - user_create: Admin create user baru
    - user_update: Admin update user
    - user_delete: Admin deactivate user
    - user_toggle_active: Admin activate/deactivate user
    - user_reset_password: Admin reset user password

Improvement:
    - Business logic extracted ke UserService
    - AJAX handling extracted ke AjaxHandler (from archive)
    - Views menjadi thin controllers (15-30 lines each)
    - Consistent dengan document_views pattern
    - Better error handling

Catatan Pemeliharaan:
    - Profile views untuk user manage profile sendiri
    - User management views untuk admin only (superuser)
    - Semua mutations menggunakan POST method
    - AJAX compatible untuk modal operations
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q

from .decorators import staff_required
from .models import User
from .forms import UserCreateForm, UserUpdateForm, ProfileEditForm
from .services import UserService
from apps.archive.services import AjaxHandler  # Reuse from archive
from apps.archive.models import Document, DocumentActivity


# ==================== HELPER FUNCTIONS ====================

def is_superuser(user):
    """Check if user is superuser"""
    return user.is_authenticated and user.is_superuser


# ==================== PROFILE VIEWS (EXISTING, IMPROVED) ====================

@login_required
def profile(request):
    """
    View: User Profile Dashboard (EXISTING, IMPROVED)
    
    Fitur:
        - User statistics (uploads, activities)
        - Recent uploads (5 latest)
        - Recent activities (10 latest)
        - Monthly upload chart (6 months)
    
    Permission:
        @login_required - User view own profile
    
    Improvements:
        - Better query optimization
        - Consistent dengan dashboard pattern
    """
    user = request.user
    
    # Get user statistics
    total_uploads = Document.objects.filter(
        created_by=user,
        is_deleted=False
    ).count()
    
    total_activities = DocumentActivity.objects.filter(
        user=user
    ).count()
    
    # Recent uploads
    recent_uploads = Document.objects.filter(
        created_by=user,
        is_deleted=False
    ).select_related('category').order_by('-created_at')[:5]
    
    # Recent activities
    recent_activities = DocumentActivity.objects.filter(
        user=user
    ).select_related('document').order_by('-created_at')[:10]
    
    # Monthly upload stats
    from django.db.models.functions import TruncMonth
    from datetime import datetime, timedelta
    
    six_months_ago = datetime.now() - timedelta(days=180)
    monthly_uploads = Document.objects.filter(
        created_by=user,
        created_at__gte=six_months_ago,
        is_deleted=False
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    context = {
        'total_uploads': total_uploads,
        'total_activities': total_activities,
        'recent_uploads': recent_uploads,
        'recent_activities': recent_activities,
        'monthly_uploads': monthly_uploads,
    }
    
    return render(request, 'accounts/profile.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def profile_edit(request):
    """
    View: Edit Own Profile (EXISTING, IMPROVED)
    
    Fitur:
        - Edit full_name, email, phone
        - Cannot edit username or permissions
        - Form validation
    
    Permission:
        @login_required - User edit own profile
    
    Improvements:
        - Better error handling
        - Consistent response pattern
    """
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil Anda berhasil diperbarui.')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Terjadi kesalahan. Mohon periksa data Anda.')
    else:
        form = ProfileEditForm(instance=request.user)
    
    context = {'form': form}
    return render(request, 'accounts/profile_edit.html', context)


# ==================== USER MANAGEMENT VIEWS (NEW) ====================

@user_passes_test(is_superuser)
@require_http_methods(["GET"])
def user_list(request):
    """
    View: List Users dengan DataTables (UPDATED)
    
    Fitur:
        - DataTables client-side processing
        - Live search (no page reload)
        - Sortable columns
        - Show document & activity counts
    
    Permission:
        @user_passes_test(is_superuser) - Superuser only
    
    Query Optimization:
        - Annotate counts untuk avoid N+1
        - Prefetch groups
        - Load ALL data (DataTables handle pagination client-side)
    
    Catatan:
        - Tidak pakai Django Paginator
        - DataTables handle search, sort, pagination di client-side
        - Cocok untuk data < 1,000 users
    """
    # Get ALL users (no pagination)
    # DataTables akan handle pagination di client-side
    users = UserService.get_users_list(
        filters=None,  # No server-side filter
        include_inactive=True  # Show all (DataTables bisa filter)
    )
    
    # Get all groups untuk filter dropdown (jika nanti diperlukan)
    from django.contrib.auth.models import Group
    all_groups = Group.objects.all()
    
    context = {
        'users': users,  # Pass queryset langsung, bukan page_obj
        'total_results': users.count(),
        'all_groups': all_groups,
    }
    
    return render(request, 'accounts/user_list.html', context)


@user_passes_test(is_superuser)
@require_http_methods(["GET", "POST"])
def user_create(request):
    """
    View: Create User Baru (NEW)
    
    Fitur:
        - Create dengan username & password
        - Set permissions (is_staff, is_superuser)
        - Assign groups
        - Support AJAX modal
    
    Permission:
        @user_passes_test(is_superuser) - Superuser only
    
    Flow:
        GET  -> Return empty form
        POST -> Validate -> Service create -> Redirect
    """
    # Initialize form
    form = UserCreateForm(request.POST or None)
    
    # POST: Process form
    if request.method == 'POST' and form.is_valid():
        try:
            # Prepare data untuk service
            data = form.cleaned_data
            groups = data.pop('groups', [])
            data.pop('password_confirm', None)  # Remove confirm field
            
            # Get group names
            group_names = [g.name for g in groups]
            data['groups'] = group_names
            data['created_by'] = request.user
            
            # Call service layer
            user = UserService.create_user(**data)
            
            # Return success response
            return AjaxHandler.handle_ajax_or_redirect(
                request=request,
                success=True,
                message=f'User "{user.username}" berhasil dibuat!',
                redirect_url='accounts:user_list'
            )
            
        except Exception as e:
            return AjaxHandler.handle_ajax_or_redirect(
                request=request,
                success=False,
                message=f'Gagal membuat user: {str(e)}',
                redirect_url='accounts:user_list'
            )
    
    # GET or invalid POST: Return form
    if AjaxHandler.is_ajax(request):
        return AjaxHandler.form_response(
            form=form,
            template='accounts/forms/user_form_content.html',
            context={'is_update': False},
            request=request,
            is_valid=form.is_valid() if request.method == 'POST' else True
        )
    
    # Fallback for non-AJAX
    return render(request, 'accounts/modals/user_form.html', {
        'form': form,
        'is_update': False
    })


@user_passes_test(is_superuser)
@require_http_methods(["GET", "POST"])
def user_update(request, pk):
    """
    View: Update User Profile & Permissions (NEW)
    
    Fitur:
        - Edit profile (name, email, phone)
        - Update permissions (is_staff, is_superuser)
        - Update groups
        - Toggle is_active
        - Support AJAX modal
    
    Permission:
        @user_passes_test(is_superuser) - Superuser only
    
    Notes:
        - Cannot edit username (identifier)
        - Cannot edit password (use reset_password)
    """
    # Get user atau 404
    user = get_object_or_404(User, pk=pk)
    
    # Prevent editing own superuser status
    if user == request.user and 'is_superuser' in request.POST:
        return AjaxHandler.handle_ajax_or_redirect(
            request=request,
            success=False,
            message='Tidak dapat mengubah status superuser sendiri',
            redirect_url='accounts:user_list'
        )
    
    # Initialize form
    form = UserUpdateForm(request.POST or None, instance=user)
    
    # POST: Process form
    if request.method == 'POST' and form.is_valid():
        try:
            # Prepare data
            data = form.cleaned_data
            groups = data.pop('groups', [])
            data['groups'] = [g.name for g in groups]
            
            # Call service layer
            updated_user = UserService.update_user(
                user=user,
                form_data=data,
                updated_by=request.user
            )
            
            # Return success response
            return AjaxHandler.handle_ajax_or_redirect(
                request=request,
                success=True,
                message=f'User "{updated_user.username}" berhasil diperbarui!',
                redirect_url='accounts:user_list'
            )
            
        except Exception as e:
            return AjaxHandler.handle_ajax_or_redirect(
                request=request,
                success=False,
                message=f'Gagal memperbarui user: {str(e)}',
                redirect_url='accounts:user_list'
            )
    
    # GET or invalid POST: Return form
    if AjaxHandler.is_ajax(request):
        return AjaxHandler.form_response(
            form=form,
            template='accounts/forms/user_form_content.html',
            context={'user': user, 'is_update': True},
            request=request,
            is_valid=form.is_valid() if request.method == 'POST' else True
        )
    
    # Fallback
    return render(request, 'accounts/modals/user_form.html', {
        'form': form,
        'user': user,
        'is_update': True
    })


@user_passes_test(is_superuser)
@require_http_methods(["POST"])
def user_delete(request, pk):
    """
    View: Deactivate User (Soft Delete) (NEW)
    
    Fitur:
        - Set is_active=False
        - User tidak bisa login
        - Data tetap tersimpan
        - Support AJAX
    
    Permission:
        @user_passes_test(is_superuser) - Superuser only
        POST only untuk keamanan
    
    Notes:
        - Soft delete, bukan hard delete
        - Bisa di-restore dengan toggle_active
        - Cannot delete own account
    """
    # Get user atau 404
    user = get_object_or_404(User, pk=pk)
    
    # Prevent deleting own account
    if user == request.user:
        return AjaxHandler.handle_ajax_or_redirect(
            request=request,
            success=False,
            message='Tidak dapat menghapus akun sendiri',
            redirect_url='accounts:user_list'
        )
    
    try:
        # Call service layer
        UserService.delete_user(
            user=user,
            deleted_by=request.user
        )
        
        # Return success
        return AjaxHandler.handle_ajax_or_redirect(
            request=request,
            success=True,
            message=f'User "{user.username}" berhasil dinonaktifkan!',
            redirect_url='accounts:user_list'
        )
        
    except Exception as e:
        return AjaxHandler.handle_ajax_or_redirect(
            request=request,
            success=False,
            message=f'Gagal menonaktifkan user: {str(e)}',
            redirect_url='accounts:user_list'
        )


@user_passes_test(is_superuser)
@require_http_methods(["POST"])
def user_toggle_active(request, pk):
    """
    View: Toggle User Active Status (NEW)
    
    Fitur:
        - Activate user yang di-deactivate
        - Deactivate user yang active
        - Support AJAX
    
    Permission:
        @user_passes_test(is_superuser) - Superuser only
        POST only
    
    Notes:
        - Berguna untuk restore user
        - Cannot toggle own status
    """
    # Get user atau 404
    user = get_object_or_404(User, pk=pk)
    
    # Prevent toggling own status
    if user == request.user:
        return AjaxHandler.handle_ajax_or_redirect(
            request=request,
            success=False,
            message='Tidak dapat mengubah status akun sendiri',
            redirect_url='accounts:user_list'
        )
    
    try:
        # Toggle status
        new_status = not user.is_active
        UserService.toggle_active_status(
            user=user,
            is_active=new_status,
            toggled_by=request.user
        )
        
        # Return success
        status_text = 'diaktifkan' if new_status else 'dinonaktifkan'
        return AjaxHandler.handle_ajax_or_redirect(
            request=request,
            success=True,
            message=f'User "{user.username}" berhasil {status_text}!',
            redirect_url='accounts:user_list'
        )
        
    except Exception as e:
        return AjaxHandler.handle_ajax_or_redirect(
            request=request,
            success=False,
            message=f'Gagal mengubah status user: {str(e)}',
            redirect_url='accounts:user_list'
        )


@user_passes_test(is_superuser)
@require_http_methods(["GET", "POST"])
def user_reset_password(request, pk):
    """
    View: Admin Reset User Password (NEW)
    
    Fitur:
        - Admin set new password untuk user
        - No need old password
        - Support AJAX modal
    
    Permission:
        @user_passes_test(is_superuser) - Superuser only
    
    Notes:
        - Untuk admin reset password user lain
        - User change password sendiri via password_change
    """
    # Get user atau 404
    user = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        new_password_confirm = request.POST.get('new_password_confirm')
        
        # Validate
        if not new_password or not new_password_confirm:
            return AjaxHandler.handle_ajax_or_redirect(
                request=request,
                success=False,
                message='Password tidak boleh kosong',
                redirect_url='accounts:user_list'
            )
        
        if new_password != new_password_confirm:
            return AjaxHandler.handle_ajax_or_redirect(
                request=request,
                success=False,
                message='Password tidak cocok',
                redirect_url='accounts:user_list'
            )
        
        # Validate strength
        result = UserService.validate_password_strength(new_password)
        if not result['is_valid']:
            return AjaxHandler.handle_ajax_or_redirect(
                request=request,
                success=False,
                message='; '.join(result['messages']),
                redirect_url='accounts:user_list'
            )
        
        try:
            # Call service layer
            UserService.change_password(
                user=user,
                new_password=new_password,
                changed_by=request.user
            )
            
            # Return success
            return AjaxHandler.handle_ajax_or_redirect(
                request=request,
                success=True,
                message=f'Password user "{user.username}" berhasil direset!',
                redirect_url='accounts:user_list'
            )
            
        except Exception as e:
            return AjaxHandler.handle_ajax_or_redirect(
                request=request,
                success=False,
                message=f'Gagal reset password: {str(e)}',
                redirect_url='accounts:user_list'
            )
    
    # GET: Return form
    if AjaxHandler.is_ajax(request):
        return AjaxHandler.form_response(
            form=None,
            template='accounts/forms/reset_password_form_content.html',
            context={'user': user},
            request=request,
            is_valid=True
        )
    
    # Fallback
    return render(request, 'accounts/modals/reset_password_form.html', {
        'user': user
    })