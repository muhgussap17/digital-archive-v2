"""
Modul: forms/filter_forms.py
Fungsi: Forms untuk filtering dan searching documents

Implementasi Standar:
    - Universal filter form untuk Document dan SPD
    - Dynamic field visibility based on is_spd parameter
    - Reusable for both list views
"""

from django import forms
from ..models import DocumentCategory, Employee, SPDDocument


class DocumentFilterForm(forms.Form):
    """
    Universal filter form untuk Document dan SPD list
    
    Field yang tampil berbeda tergantung is_spd parameter:
        - Document (Belanjaan): search, category, date_from, date_to
        - SPD: search, employee, destination, date_from, date_to
    
    Args:
        is_spd (bool): True untuk SPD list, False untuk document list
    
    Examples:
        >>> # Untuk document list
        >>> form = DocumentFilterForm(request.GET or None, is_spd=False)
        
        >>> # Untuk SPD list
        >>> form = DocumentFilterForm(request.GET or None, is_spd=True)
    
    Implementasi Standar:
        - Dynamic form configuration di __init__
        - Hidden fields untuk fields yang tidak dipakai
        - Consistent field attributes
    """
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Cari dokumen...',
            'id': 'searchInput'
        }),
        label='Pencarian'
    )
    
    category = forms.ModelChoiceField(
        queryset=DocumentCategory.objects.filter(parent__isnull=True),
        required=False,
        empty_label="Semua Kategori",
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        label='Kategori'
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control datepicker',
            'placeholder': 'Dari tanggal',
            'autocomplete': 'off',
            'data-date-format': 'dd/mm/yyyy',
        }),
        input_formats=['%Y-%m-%d', '%d/%m/%Y'],
        label='Dari Tanggal'
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control datepicker',
            'placeholder': 'Sampai tanggal',
            'autocomplete': 'off',
            'data-date-format': 'dd/mm/yyyy',
        }),
        input_formats=['%Y-%m-%d', '%d/%m/%Y'],
        label='Sampai Tanggal'
    )
    
    # SPD-specific fields
    employee = forms.ModelChoiceField(
        queryset=Employee.objects.filter(is_active=True),
        required=False,
        empty_label="Semua Pegawai",
        widget=forms.Select(attrs={
            'class': 'form-control',
            'data-allow-clear': 'true'
        }),
        label='Nama Pegawai'
    )
    
    destination = forms.ChoiceField(
        choices=[('', 'Semua Tujuan')],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        label='Tujuan'
    )
    
    def __init__(self, *args, is_spd=False, **kwargs):
        """
        Initialize form dengan dynamic field configuration
        
        Args:
            is_spd: True untuk SPD mode, False untuk document mode
        """
        super().__init__(*args, **kwargs)
        
        # Populate destination choices
        self.fields['destination'].choices = [
            ('', 'Semua Tujuan')
        ] + list(SPDDocument.DESTINATION_CHOICES)
        
        if is_spd:
            # SPD mode: hide category, show employee & destination
            self.fields['category'].widget = forms.HiddenInput()
            self.fields['category'].required = False
            self.fields['search'].widget.attrs['placeholder'] = 'Cari nama pegawai atau tujuan...'
        else:
            # Document mode: hide employee & destination
            self.fields['employee'].widget = forms.HiddenInput()
            self.fields['employee'].required = False
            self.fields['destination'].widget = forms.HiddenInput()
            self.fields['destination'].required = False