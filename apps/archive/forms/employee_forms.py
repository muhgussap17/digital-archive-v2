"""
Modul: forms/employee_forms.py
Fungsi: Forms untuk Employee management

Implementasi Standar:
    - ModelForm untuk Employee CRUD
    - Validation untuk NIP format
"""

from django import forms
from django.core.exceptions import ValidationError

from ..models import Employee
from ..constants import NIP_LENGTH


class EmployeeForm(forms.ModelForm):
    """
    Form untuk pengelolaan data pegawai
    
    Fields:
        - nip: NIP pegawai (18 digit)
        - name: Nama lengkap
        - position: Jabatan
        - department: Unit kerja
        - is_active: Status aktif
    
    Validation:
        - NIP harus 18 digit angka
        - NIP harus unique
    
    Examples:
        >>> form = EmployeeForm(data={...})
        >>> if form.is_valid():
        ...     employee = form.save()
    
    Implementasi Standar:
        - NIP validation sesuai standar PNS
        - Consistent field attributes dengan Bootstrap Argon
    """
    
    class Meta:
        model = Employee
        fields = ['nip', 'name', 'position', 'department', 'is_active']
        widgets = {
            'nip': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Contoh: 198501012010011001',
                'required': True
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nama lengkap pegawai',
                'required': True
            }),
            'position': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Contoh: Staf Administrasi',
                'required': True
            }),
            'department': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Contoh: Bagian Umum',
                'required': True
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'custom-control-input',
            }),
        }
        labels = {
            'nip': 'NIP',
            'name': 'Nama Lengkap',
            'position': 'Jabatan',
            'department': 'Unit Kerja',
            'is_active': 'Status Aktif',
        }
    
    def clean_nip(self):
        """
        Validasi NIP format
        
        Rules:
            1. Remove spaces dan dashes
            2. Must be numeric
            3. Must be 18 digits (standard PNS)
        
        Returns:
            str: Cleaned NIP
            
        Raises:
            ValidationError: Jika NIP tidak valid
        """
        nip = self.cleaned_data.get('nip')
        
        if nip:
            # Remove spaces and dashes
            nip = nip.replace(' ', '').replace('-', '')
            
            # Check if numeric
            if not nip.isdigit():
                raise ValidationError('NIP harus berupa angka')
            
            # Check length
            if len(nip) != NIP_LENGTH:
                raise ValidationError(f'NIP harus {NIP_LENGTH} digit')
        
        return nip