"""
Modul: apps/accounts/forms.py (REFACTORED)
Fungsi: Forms untuk User management dengan mixins pattern

Berisi forms:
    - UserCreateForm: Create user baru dengan password
    - UserUpdateForm: Update user profile & permissions
    - ProfileEditForm: User edit profile sendiri
    - PasswordChangeForm: Change password (existing, improved)

Implementasi Standar:
    - Menggunakan mixins untuk DRY principle
    - Consistent dengan DocumentForm pattern
    - Bootstrap Argon compatible widgets
    - Strong validation

Catatan Pemeliharaan:
    - UserCreateForm untuk admin create user
    - UserUpdateForm untuk admin edit user
    - ProfileEditForm untuk user edit sendiri (limited fields)
    - Semua forms menggunakan Bootstrap Argon styling
    
Cara Penggunaan:
    # Admin create user
    form = UserCreateForm(request.POST)
    if form.is_valid():
        user = UserService.create_user(**form.cleaned_data)
    
    # Admin update user
    form = UserUpdateForm(request.POST, instance=user)
    if form.is_valid():
        UserService.update_user(user, form.cleaned_data)
    
    # User edit profile
    form = ProfileEditForm(request.POST, instance=request.user)
    if form.is_valid():
        form.save()
"""

from django import forms
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from .models import User


# ==================== FORM MIXINS ====================

class BootstrapFormMixin:
    """
    Mixin untuk add Bootstrap Argon classes ke form fields
    
    Automatically add 'form-control' class ke semua input fields
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():  # type: ignore
            # Skip checkbox fields (custom-control-input)
            if isinstance(field.widget, forms.CheckboxInput):
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'custom-control-input'
            else:
                # Add form-control to other inputs
                existing_classes = field.widget.attrs.get('class', '')
                if 'form-control' not in existing_classes:
                    field.widget.attrs['class'] = f'{existing_classes} form-control'.strip()


class UsernameFieldMixin:
    """
    Mixin untuk username field dengan validation
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['username'] = forms.CharField(  # type: ignore
            max_length=150,
            required=True,
            widget=forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Contoh: johndoe',
                'autocomplete': 'username'
            }),
            label='Username',
            help_text='Required. 150 karakter atau kurang. Hanya huruf, angka, dan @/./+/-/_ '
        )
    
    def clean_username(self):
        """Validate username uniqueness (untuk create)"""
        username = self.cleaned_data.get('username')  # type: ignore
        
        if username:
            # Check uniqueness (exclude current instance untuk update)
            queryset = User.objects.filter(username=username)
            
            # Untuk update, exclude instance saat ini
            if hasattr(self, 'instance') and self.instance.pk:  # type: ignore
                queryset = queryset.exclude(pk=self.instance.pk)  # type: ignore
            
            if queryset.exists():
                raise ValidationError('Username sudah digunakan.')
        
        return username


class PasswordFieldMixin:
    """
    Mixin untuk password fields (create only)
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['password'] = forms.CharField(  # type: ignore
            required=True,
            widget=forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Minimal 8 karakter',
                'autocomplete': 'new-password'
            }),
            label='Password',
            help_text='Minimal 8 karakter. Kombinasi huruf, angka, dan simbol.'
        )
        
        self.fields['password_confirm'] = forms.CharField(  # type: ignore
            required=True,
            widget=forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ulangi password',
                'autocomplete': 'new-password'
            }),
            label='Konfirmasi Password'
        )
    
    def clean(self):
        """Validate password match"""
        cleaned_data = super().clean()  # type: ignore
        
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password_confirm:
            if password != password_confirm:
                raise ValidationError({
                    'password_confirm': 'Password tidak cocok'
                })
        
        return cleaned_data


class ProfileFieldsMixin:
    """
    Mixin untuk basic profile fields (full_name, email, phone)
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['full_name'] = forms.CharField(  # type: ignore
            max_length=255,
            required=True,
            widget=forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nama lengkap user'
            }),
            label='Nama Lengkap'
        )
        
        self.fields['email'] = forms.EmailField(  # type: ignore
            required=False,
            widget=forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@example.com'
            }),
            label='Email'
        )
        
        self.fields['phone'] = forms.CharField(  # type: ignore
            max_length=20,
            required=False,
            widget=forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '08xxxxxxxxxx'
            }),
            label='Nomor Telepon'
        )


class PermissionFieldsMixin:
    """
    Mixin untuk permission fields (is_staff, is_superuser, groups)
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['is_staff'] = forms.BooleanField(  # type: ignore
            required=False,
            widget=forms.CheckboxInput(attrs={
                'class': 'custom-control-input'
            }),
            label='Status Staff',
            help_text='Beri akses ke halaman admin dan fitur CRUD'
        )
        
        self.fields['is_superuser'] = forms.BooleanField(  # type: ignore
            required=False,
            widget=forms.CheckboxInput(attrs={
                'class': 'custom-control-input'
            }),
            label='Status Superuser',
            help_text='Beri semua permissions tanpa perlu assign explicit'
        )
        
        self.fields['groups'] = forms.ModelMultipleChoiceField(  # type: ignore
            queryset=Group.objects.all(),
            required=False,
            widget=forms.SelectMultiple(attrs={
                'class': 'form-control select2',
                'multiple': 'multiple'
            }),
            label='Groups',
            help_text='Assign user ke groups untuk permissions'
        )


# ==================== USER FORMS ====================

class UserCreateForm(
    UsernameFieldMixin,
    PasswordFieldMixin,
    ProfileFieldsMixin,
    PermissionFieldsMixin,
    BootstrapFormMixin,
    forms.Form
):
    """
    Form untuk admin create user baru
    
    Fields (dari mixins):
        - username: Username untuk login (UsernameFieldMixin)
        - password: Password (PasswordFieldMixin)
        - password_confirm: Konfirmasi password (PasswordFieldMixin)
        - full_name: Nama lengkap (ProfileFieldsMixin)
        - email: Email address (ProfileFieldsMixin)
        - phone: Nomor telepon (ProfileFieldsMixin)
        - is_staff: Staff status (PermissionFieldsMixin)
        - is_superuser: Superuser status (PermissionFieldsMixin)
        - groups: Group assignment (PermissionFieldsMixin)
    
    Validation (dari mixins):
        - Username uniqueness (UsernameFieldMixin)
        - Password match (PasswordFieldMixin)
        - Bootstrap styling (BootstrapFormMixin)
    
    Examples:
        >>> form = UserCreateForm(data={
        ...     'username': 'johndoe',
        ...     'password': 'securepass123',
        ...     'password_confirm': 'securepass123',
        ...     'full_name': 'John Doe',
        ...     'email': 'john@example.com',
        ...     'is_staff': True,
        ...     'groups': [staff_group]
        ... })
        >>> if form.is_valid():
        ...     user = UserService.create_user(**form.cleaned_data)
    
    Implementasi Standar:
        - Menggunakan mixins untuk DRY
        - Validation logic terisolasi di mixins
        - Bootstrap Argon compatible
    """
    
    def clean_password(self):
        """Validate password strength"""
        from apps.accounts.services import UserService
        
        password = self.cleaned_data.get('password')
        
        if password:
            # Validate strength
            result = UserService.validate_password_strength(password)
            if not result['is_valid']:
                raise ValidationError(result['messages'])
        
        return password


class UserUpdateForm(
    ProfileFieldsMixin,
    PermissionFieldsMixin,
    BootstrapFormMixin,
    forms.ModelForm
):
    """
    Form untuk admin update user profile & permissions
    
    Fields (dari mixins):
        - full_name: Nama lengkap (ProfileFieldsMixin)
        - email: Email address (ProfileFieldsMixin)
        - phone: Nomor telepon (ProfileFieldsMixin)
        - is_staff: Staff status (PermissionFieldsMixin)
        - is_superuser: Superuser status (PermissionFieldsMixin)
        - groups: Group assignment (PermissionFieldsMixin)
        - is_active: Active status (dari Meta)
        - NO USERNAME (cannot change)
        - NO PASSWORD (use separate change_password)
    
    Notes:
        - Username tidak bisa diubah (identifier)
        - Password tidak bisa diubah di sini (gunakan change_password)
        - is_active untuk activate/deactivate user
    
    Examples:
        >>> form = UserUpdateForm(data={...}, instance=user)
        >>> if form.is_valid():
        ...     UserService.update_user(user, form.cleaned_data)
    
    Implementasi Standar:
        - ModelForm untuk populate existing data
        - Reuse mixins untuk consistency
        - Exclude username dan password
    """
    
    class Meta:  # type: ignore
        model = User
        fields = [
            'full_name', 'email', 'phone',
            'is_staff', 'is_superuser', 'is_active',
            'groups'
        ]
        widgets = {
            'is_active': forms.CheckboxInput(attrs={
                'class': 'custom-control-input'
            })
        }
        labels = {
            'is_active': 'Status Aktif'
        }
        help_texts = {
            'is_active': 'Nonaktifkan untuk melarang user login'
        }


class ProfileEditForm(ProfileFieldsMixin, BootstrapFormMixin, forms.ModelForm):
    """
    Form untuk user edit profile sendiri (limited fields)
    
    Fields (dari mixins):
        - full_name: Nama lengkap (ProfileFieldsMixin)
        - email: Email address (ProfileFieldsMixin)
        - phone: Nomor telepon (ProfileFieldsMixin)
        - NO USERNAME (cannot change)
        - NO PASSWORD (use password_change)
        - NO PERMISSIONS (admin only)
    
    Notes:
        - User hanya bisa edit profile sendiri
        - Tidak bisa ubah username atau permissions
        - Password change via separate form
    
    Examples:
        >>> form = ProfileEditForm(data={...}, instance=request.user)
        >>> if form.is_valid():
        ...     form.save()
    
    Implementasi Standar:
        - Minimal fields untuk security
        - Bootstrap styling via mixin
    """
    
    class Meta:  # type: ignore
        model = User
        fields = ['full_name', 'email', 'phone']


class CustomUserChangeForm(UserChangeForm):
    """
    Form kustom untuk digunakan di Django Admin (EXISTING, IMPROVED)
    
    Ini memastikan field kustom (full_name, phone) muncul di admin panel.
    Sudah ada di file asli, hanya improve documentation.
    """
    
    class Meta(UserChangeForm.Meta):  # type: ignore
        model = User
        fields = (
            'username', 'email', 'full_name', 'phone',
            'is_active', 'is_staff', 'is_superuser',
            'groups', 'user_permissions'
        )