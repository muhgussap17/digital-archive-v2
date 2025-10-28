from django import forms
from django.core.exceptions import ValidationError
from .models import Document, DocumentCategory, SPDDocument, Employee
from .utils import validate_pdf_file


class DocumentUploadForm(forms.ModelForm):
    """Base form for document upload"""
    
    category = forms.ModelChoiceField(
        queryset=DocumentCategory.objects.filter(parent__isnull=False),
        empty_label="-- Pilih Kategori --",
        widget=forms.Select(attrs={
            'class': 'form-control',
            'required': True
        }),
        label='Kategori Dokumen'
    )
    
    document_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control datepicker',
            'placeholder': 'Pilih tanggal',
            'autocomplete': 'off',
            'data-date-format': 'dd/mm/yyyy',
        }),
        input_formats=['%Y-%m-%d', '%d/%m/%Y'],
        label='Tanggal Dokumen'
    )
    
    file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control-file',
            'accept': 'application/pdf',
            'required': True
        }),
        label='File PDF',
        help_text='Maksimal 10MB, format PDF'
    )
    
    class Meta:
        model = Document
        fields = ['category', 'document_date', 'file']
    
    def clean_file(self):
        """Validate PDF file"""
        file = self.cleaned_data.get('file')
        
        if file:
            is_valid, error_msg = validate_pdf_file(file)
            if not is_valid:
                raise ValidationError(error_msg) # type: ignore
        
        return file
    
    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        
        # Additional validation based on category
        if category and category.slug == 'spd':
            raise ValidationError({
                'category': 'Untuk dokumen SPD, gunakan form khusus SPD'
            })
        
        return cleaned_data


class SPDDocumentForm(forms.Form):
    """Form for SPD document upload with employee info"""
    
    document_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control datepicker',
            'placeholder': 'Pilih tanggal',
            'autocomplete': 'off',
            'data-date-format': 'dd/mm/yyyy',
        }),
        input_formats=['%Y-%m-%d', '%d/%m/%Y'],
        label='Tanggal SPD'
    )
    
    file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control-file',
            'accept': 'application/pdf',
            'required': True
        }),
        label='File PDF',
        help_text='Maksimal 10MB, format PDF'
    )
    
    employee = forms.ModelChoiceField(
        queryset=Employee.objects.filter(is_active=True),
        empty_label="-- Pilih Pegawai --",
        widget=forms.Select(attrs={
            'class': 'form-control select2',
            'required': True
        }),
        label='Nama Pegawai'
    )
    
    destination = forms.ChoiceField(
        choices=SPDDocument.DESTINATION_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'required': True,
            'onchange': 'toggleDestinationOther(this)'
        }),
        label='Tujuan'
    )
    
    destination_other = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Isi jika memilih "Lainnya"',
            'id': 'destination_other_field'
        }),
        label='Tujuan Lainnya'
    )
    
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control datepicker',
            'placeholder': 'Tanggal mulai',
            'autocomplete': 'off',
            'data-date-format': 'dd/mm/yyyy',
        }),
        input_formats=['%Y-%m-%d', '%d/%m/%Y'],
        label='Tanggal Mulai'
    )
    
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control datepicker',
            'placeholder': 'Tanggal selesai',
            'autocomplete': 'off',
            'data-date-format': 'dd/mm/yyyy',
        }),
        input_formats=['%Y-%m-%d', '%d/%m/%Y'],
        label='Tanggal Selesai'
    )
    
    def clean_file(self):
        """Validate PDF file"""
        file = self.cleaned_data.get('file')
        
        if file:
            is_valid, error_msg = validate_pdf_file(file)
            if not is_valid:
                raise ValidationError(error_msg) # pyright: ignore[reportArgumentType]
        
        return file
    
    def clean(self):
        cleaned_data = super().clean()
        
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        destination = cleaned_data.get('destination')
        destination_other = cleaned_data.get('destination_other')
        
        # Validate date range
        if start_date and end_date:
            if end_date < start_date:
                raise ValidationError({
                    'end_date': 'Tanggal selesai harus setelah atau sama dengan tanggal mulai'
                })
        
        # Validate destination_other
        if destination == 'other' and not destination_other:
            raise ValidationError({
                'destination_other': 'Harap isi tujuan lainnya'
            })
        
        return cleaned_data


class DocumentFilterForm(forms.Form):
    """Form for filtering documents"""
    
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
            'onchange': 'this.form.submit()'
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
    
    employee = forms.ModelChoiceField(
        queryset=Employee.objects.filter(is_active=True),
        required=False,
        empty_label="Semua Pegawai",
        widget=forms.Select(attrs={
            'class': 'form-control select2',
            'onchange': 'this.form.submit()'
        }),
        label='Pegawai (SPD)'
    )


class EmployeeForm(forms.ModelForm):
    """Form for employee management"""
    
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
        """Validate NIP format"""
        nip = self.cleaned_data.get('nip')
        
        if nip:
            # Remove spaces and dashes
            nip = nip.replace(' ', '').replace('-', '')
            
            # Check if numeric
            if not nip.isdigit():
                raise ValidationError('NIP harus berupa angka')
            
            # Check length (18 digits standard for PNS)
            if len(nip) != 18:
                raise ValidationError('NIP harus 18 digit')
        
        return nip


class DocumentUpdateForm(forms.ModelForm):
    """Form for updating document metadata"""
    
    document_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control datepicker',
            'placeholder': 'Pilih tanggal',
            'autocomplete': 'off',
            'data-date-format': 'dd/mm/yyyy',
        }),
        input_formats=['%Y-%m-%d', '%d/%m/%Y'],
        label='Tanggal Dokumen'
    )
    