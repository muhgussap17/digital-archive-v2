"""
Modul: forms/mixins.py
Fungsi: Reusable form field mixins untuk mengurangi duplikasi kode

Berisi mixins untuk:
    - DateFieldMixin: Field tanggal dengan datepicker
    - DateRangeValidationMixin: Validasi range tanggal (start-end)
    - FileFieldMixin: Field upload file PDF
    - EmployeeFieldMixin: Field pemilihan pegawai
    - DestinationFieldMixin: Field pemilihan tujuan SPD

Implementasi Standar:
    - Mengikuti Django Forms best practices
    - DRY (Don't Repeat Yourself) principle
    - Consistent field configuration
    - Reusable validation logic

Catatan Pemeliharaan:
    - Jangan hardcode widget attributes, gunakan class variables
    - Semua widget styling harus konsisten dengan Bootstrap Argon theme
    - Update DATEPICKER_ATTRS jika ada perubahan theme/library
    
Cara Penggunaan:
    class MyForm(DateFieldMixin, forms.Form):
        # Otomatis dapat field 'document_date' dengan datepicker
        pass
        
    class MySPDForm(DateFieldMixin, EmployeeFieldMixin, forms.Form):
        # Dapat 'document_date' dan 'employee' fields
        pass
"""

from django import forms
from datetime import date
from django.core.exceptions import ValidationError

from ..models import Employee, SPDDocument, DocumentCategory
from ..constants import DESTINATION_OTHER_KEY


# ==================== SHARED CONFIGURATIONS ====================

# Datepicker widget attributes (Bootstrap Argon compatible)
DATEPICKER_ATTRS = {
    'class': 'form-control datepicker',
    'autocomplete': 'off',
    'data-date-format': 'dd/mm/yyyy',
}

# File input widget attributes
FILE_INPUT_ATTRS = {
    'class': 'custom-file-input',
    'id': 'customFileLang',
    'lang': 'en',
    'accept': 'application/pdf',
    'required': True
}

# Standard select widget attributes
SELECT_ATTRS = {
    'class': 'form-control',
    'required': True
}

# Date input formats (ISO and Indonesian)
DATE_INPUT_FORMATS = ['%Y-%m-%d', '%d/%m/%Y']


# ==================== DATE FIELD MIXINS ====================

class DateFieldMixin:
    """
    Mixin untuk menambahkan field tanggal dengan datepicker
    
    Menambahkan field 'document_date' dengan konfigurasi standar:
        - Bootstrap datepicker widget
        - Format Indonesia (dd/mm/yyyy)
        - Validation: tidak boleh di masa depan
    
    Attributes:
        document_date_label: Label untuk field (default: 'Tanggal Dokumen')
        document_date_placeholder: Placeholder text (default: 'Pilih tanggal')
    
    Examples:
        >>> class MyForm(DateFieldMixin, forms.Form):
        ...     pass
        >>> form = MyForm()
        >>> 'document_date' in form.fields
        True
    
    Implementasi Standar:
        - Sesuai dengan UI/UX requirements Bootstrap Argon
        - Format tanggal mengikuti standar Indonesia
    """
    
    # Override these in subclass if needed
    document_date_label = 'Tanggal Dokumen'
    document_date_placeholder = 'Pilih tanggal'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add document_date field
        self.fields['document_date'] = forms.DateField( # type: ignore
            widget=forms.DateInput(attrs={
                **DATEPICKER_ATTRS,
                'placeholder': self.document_date_placeholder,
            }),
            input_formats=DATE_INPUT_FORMATS,
            label=self.document_date_label,
            required=True
        )
    
    def clean_document_date(self):
        """
        Validasi document_date tidak boleh di masa depan
        
        Returns:
            date: Validated document_date
            
        Raises:
            ValidationError: Jika tanggal melebihi hari ini
        """
        document_date = self.cleaned_data.get('document_date') # type: ignore
        
        if document_date and document_date > date.today():
            raise ValidationError('Tanggal dokumen tidak boleh melebihi hari ini.')
        
        return document_date


class DateRangeFieldMixin:
    """
    Mixin untuk menambahkan field range tanggal (start_date, end_date)
    
    Menambahkan 2 fields:
        - start_date: Tanggal mulai
        - end_date: Tanggal selesai
    
    Attributes:
        start_date_label: Label untuk start_date (default: 'Tanggal Mulai')
        end_date_label: Label untuk end_date (default: 'Tanggal Selesai')
    
    Examples:
        >>> class MySPDForm(DateRangeFieldMixin, forms.Form):
        ...     pass
        >>> form = MySPDForm()
        >>> 'start_date' in form.fields and 'end_date' in form.fields
        True
    """
    
    # Override these in subclass if needed
    start_date_label = 'Tanggal Mulai'
    end_date_label = 'Tanggal Selesai'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add start_date field
        self.fields['start_date'] = forms.DateField( # type: ignore
            widget=forms.DateInput(attrs={
                **DATEPICKER_ATTRS,
                'placeholder': 'Tanggal Mulai',
            }),
            input_formats=DATE_INPUT_FORMATS,
            label=self.start_date_label,
            required=True
        )
        
        # Add end_date field
        self.fields['end_date'] = forms.DateField( # type: ignore
            widget=forms.DateInput(attrs={
                **DATEPICKER_ATTRS,
                'placeholder': 'Tanggal Selesai',
            }),
            input_formats=DATE_INPUT_FORMATS,
            label=self.end_date_label,
            required=True
        )


class DateRangeValidationMixin:
    """
    Mixin untuk validasi date range (start_date <= end_date)
    
    Memvalidasi:
        1. start_date tidak boleh di masa depan
        2. end_date tidak boleh di masa depan
        3. end_date harus >= start_date
    
    Catatan:
        - Harus digunakan bersama DateRangeFieldMixin
        - Atau form harus punya start_date dan end_date fields
    
    Examples:
        >>> class MySPDForm(DateRangeFieldMixin, DateRangeValidationMixin, forms.Form):
        ...     pass
    """
    
    def clean_start_date(self):
        """Validasi start_date tidak di masa depan"""
        start_date = self.cleaned_data.get('start_date') # type: ignore
        
        if start_date and start_date > date.today():
            raise ValidationError('Tanggal mulai tidak boleh melebihi hari ini.')
        
        return start_date
    
    def clean_end_date(self):
        """Validasi end_date tidak di masa depan"""
        end_date = self.cleaned_data.get('end_date') # type: ignore
        
        if end_date and end_date > date.today():
            raise ValidationError('Tanggal selesai tidak boleh melebihi hari ini.')
        
        return end_date
    
    def clean(self):
        """Validasi end_date >= start_date"""
        cleaned_data = super().clean() # type: ignore
        
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if end_date < start_date:
                raise ValidationError({
                    'end_date': 'Tanggal selesai harus setelah atau sama dengan tanggal mulai'
                })
        
        return cleaned_data


# ==================== FILE FIELD MIXIN ====================

class FileFieldMixin:
    """
    Mixin untuk menambahkan field upload file PDF
    
    Menambahkan field 'file' dengan:
        - Custom file input widget (Bootstrap Argon style)
        - Accept PDF only
        - Validasi file menggunakan validate_pdf_file dari utils
    
    Attributes:
        file_label: Label untuk field (default: 'File PDF')
        file_help_text: Help text (default: 'Maksimal 10MB, format PDF')
    
    Examples:
        >>> class MyForm(FileFieldMixin, forms.Form):
        ...     pass
        >>> form = MyForm()
        >>> 'file' in form.fields
        True
    
    Implementasi Standar:
        - Validasi menggunakan utils.validate_pdf_file
        - Max file size dari constants
    """
    
    # Override these in subclass if needed
    file_label = 'File PDF'
    file_help_text = 'Maksimal 10MB, format PDF'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add file field
        self.fields['file'] = forms.FileField( # type: ignore
            widget=forms.FileInput(attrs=FILE_INPUT_ATTRS),
            label=self.file_label,
            help_text=self.file_help_text,
            required=True
        )
    
    def clean_file(self):
        """
        Validasi file PDF menggunakan validate_pdf_file
        
        Returns:
            File: Validated file object
            
        Raises:
            ValidationError: Jika file tidak valid
        """
        from ..utils import validate_pdf_file
        
        file = self.cleaned_data.get('file') # type: ignore
        
        if file:
            is_valid, error_msg = validate_pdf_file(file)
            if not is_valid:
                raise ValidationError(error_msg) # type: ignore
        
        return file


# ==================== EMPLOYEE & DESTINATION MIXINS ====================

class EmployeeFieldMixin:
    """
    Mixin untuk menambahkan field pemilihan pegawai
    
    Menambahkan field 'employee' dengan:
        - ModelChoiceField linked to Employee model
        - Filter hanya active employees
        - Select2-compatible attributes
    
    Attributes:
        employee_label: Label untuk field (default: 'Nama Pegawai')
        employee_required: Required atau tidak (default: True)
    
    Examples:
        >>> class MySPDForm(EmployeeFieldMixin, forms.Form):
        ...     pass
        >>> form = MySPDForm()
        >>> 'employee' in form.fields
        True
    """
    
    # Override these in subclass if needed
    employee_label = 'Nama Pegawai'
    employee_required = True
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add employee field
        self.fields['employee'] = forms.ModelChoiceField( # type: ignore
            queryset=Employee.objects.filter(is_active=True),
            empty_label="Pilih Pegawai",
            widget=forms.Select(attrs=SELECT_ATTRS),
            label=self.employee_label,
            required=self.employee_required
        )


class DestinationFieldMixin:
    """
    Mixin untuk menambahkan field tujuan perjalanan
    
    Menambahkan 2 fields:
        - destination: ChoiceField dengan DESTINATION_CHOICES
        - destination_other: CharField untuk "Lainnya"
    
    Validasi:
        - Jika destination='other', destination_other wajib diisi
    
    Attributes:
        destination_label: Label untuk destination (default: 'Tujuan')
        destination_other_label: Label untuk destination_other (default: 'Tujuan Lainnya')
    
    Examples:
        >>> class MySPDForm(DestinationFieldMixin, forms.Form):
        ...     pass
        >>> form = MySPDForm()
        >>> 'destination' in form.fields and 'destination_other' in form.fields
        True
    """
    
    # Override these in subclass if needed
    destination_label = 'Tujuan'
    destination_other_label = 'Tujuan Lainnya'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add destination field
        self.fields['destination'] = forms.ChoiceField( # type: ignore
            choices=SPDDocument.DESTINATION_CHOICES,
            widget=forms.Select(attrs={
                **SELECT_ATTRS,
                'onchange': 'toggleDestinationOther(this)'
            }),
            label=self.destination_label,
            required=True
        )
        
        # Add destination_other field
        self.fields['destination_other'] = forms.CharField( # type: ignore
            max_length=255,
            required=False,
            widget=forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Isi jika memilih "Lainnya"',
                'id': 'destination_other_field'
            }),
            label=self.destination_other_label
        )
    
    def clean(self):
        """
        Validasi destination_other wajib jika destination='other'
        
        Returns:
            dict: Cleaned data
            
        Raises:
            ValidationError: Jika destination='other' tapi destination_other kosong
        """
        cleaned_data = super().clean() # type: ignore
        
        destination = cleaned_data.get('destination')
        destination_other = cleaned_data.get('destination_other')
        
        if destination == DESTINATION_OTHER_KEY and not destination_other:
            raise ValidationError({
                'destination_other': 'Harap isi tujuan lainnya'
            })
        
        return cleaned_data


# ==================== CATEGORY FIELD MIXIN ====================

class CategoryFieldMixin:
    """
    Mixin untuk menambahkan field kategori dokumen
    
    Menambahkan field 'category' dengan:
        - ModelChoiceField linked to DocumentCategory
        - Filter hanya subcategories (parent__isnull=False)
        - Validasi tidak boleh kategori SPD
    
    Attributes:
        category_label: Label untuk field (default: 'Kategori Dokumen')
    
    Examples:
        >>> class MyDocForm(CategoryFieldMixin, forms.Form):
        ...     pass
        >>> form = MyDocForm()
        >>> 'category' in form.fields
        True
    """
    
    # Override in subclass if needed
    category_label = 'Kategori Dokumen'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add category field (only subcategories)
        self.fields['category'] = forms.ModelChoiceField( # type: ignore
            queryset=DocumentCategory.objects.filter(parent__isnull=False),
            empty_label=" Pilih Kategori ",
            widget=forms.Select(attrs=SELECT_ATTRS),
            label=self.category_label,
            required=True
        )
    
    def clean_category(self):
        """
        Validasi category tidak boleh SPD
        
        Returns:
            DocumentCategory: Validated category
            
        Raises:
            ValidationError: Jika category adalah SPD
        """
        category = self.cleaned_data.get('category') # type: ignore
        
        if category and category.slug == 'spd':
            raise ValidationError('Untuk dokumen SPD, gunakan form khusus SPD')
        
        return category