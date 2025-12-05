"""
Modul: apps/accounts/urls.py (REFACTORED & EXTENDED)
Fungsi: URL routing untuk accounts app

Routes:
    AUTHENTICATION:
    - login: Login page
    - logout: Logout action
    - password_change: User change own password
    - password_change_done: Success page
    
    PROFILE:
    - profile: User profile dashboard
    - profile_edit: Edit own profile
    
    USER MANAGEMENT (NEW):
    - user_list: List all users (superuser only)
    - user_create: Create new user (superuser only)
    - user_update: Edit user (superuser only)
    - user_delete: Deactivate user (superuser only)
    - user_toggle_active: Toggle user status (superuser only)
    - user_reset_password: Reset user password (superuser only)

Implementasi Standar:
    - RESTful URL patterns
    - Consistent naming convention
    - Clear separation of concerns
"""

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    # ==================== AUTHENTICATION ====================
    path('login/', auth_views.LoginView.as_view(
        template_name='accounts/login.html'
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # ==================== USER SELF-MANAGEMENT (All User) ====================
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('password-change/', auth_views.PasswordChangeView.as_view(
        template_name='accounts/password_change.html',
        success_url='/accounts/password-change/done/'
    ), name='password_change'),
    path('password-change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='accounts/password_change_done.html'
    ), name='password_change_done'),
    
    # ==================== USER MANAGEMENT (Superuser Only) ====================
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:pk>/update/', views.user_update, name='user_update'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),
    path('users/<int:pk>/toggle-active/', views.user_toggle_active, name='user_toggle_active'),
    path('users/<int:pk>/reset-password/', views.user_reset_password, name='user_reset_password'),
]