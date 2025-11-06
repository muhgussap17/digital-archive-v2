from django import forms
from django.contrib.auth.forms import UserChangeForm
from .models import User

class ProfileEditForm(forms.ModelForm):
    """
    Form untuk pengguna mengedit data profil mereka sendiri di halaman frontend.
    """
    class Meta:
        model = User
        fields = ['full_name', 'email', 'phone']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }

class CustomUserChangeForm(UserChangeForm):
    """
    Form kustom untuk digunakan di Django Admin.
    Ini memastikan field kustom (full_name, phone) muncul di admin panel.
    """
    class Meta(UserChangeForm.Meta): # type: ignore
        model = User
        fields = ('username', 'email', 'full_name', 'phone', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')