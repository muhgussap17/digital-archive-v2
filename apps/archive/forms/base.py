"""
Modul: forms/base.py
Fungsi: Base form classes dengan common logic

Berisi base classes untuk:
    - BaseDocumentForm: Base untuk DocumentForm dan DocumentUpdateForm
    - BaseSPDForm: Base untuk SPDDocumentForm dan SPDDocumentUpdateForm

Implementasi Standar:
    - Inheritance hierarchy untuk code reuse
    - Shared validation logic
    - Consistent error handling

Catatan Pemeliharaan:
    - Semua document forms harus inherit dari BaseDocumentForm
    - Semua SPD forms harus inherit dari BaseSPDForm
    - Jangan tambah business logic di sini, hanya form logic
    
Cara Penggunaan:
    class DocumentForm(CategoryFieldMixin, DateFieldMixin, FileFieldMixin, BaseDocumentForm):
        class Meta:
            model = Document
            fields = ['category', 'document_date', 'file']
"""

from django import forms
from django.core.exceptions import ValidationError

from ..models import Document


class BaseDocumentForm(forms.ModelForm):
    """
    Base form untuk semua document forms (belanjaan)
    
    Menyediakan:
        - Common Meta configuration
        - Shared validation logic
        - Error handling
    
    Digunakan oleh:
        - DocumentForm (create)
        - DocumentUpdateForm (update metadata only)
    
    Catatan:
        - Tidak define fields di sini, biar subclass yang define
        - Validation logic shared antara create dan update
    """
    
    class Meta:
        model = Document
        fields = []  # Will be overridden by subclass
    
    def clean(self):
        """
        Common validation untuk document forms
        
        Validates:
            - Category tidak boleh SPD (handled by CategoryFieldMixin)
            - Document date validation (handled by DateFieldMixin)
        
        Returns:
            dict: Cleaned data
        """
        cleaned_data = super().clean()
        
        # Additional validations can be added here
        # that are common to all document forms
        
        return cleaned_data


class BaseSPDForm(forms.Form):
    """
    Base form untuk semua SPD forms
    
    Menyediakan:
        - Common validation logic untuk SPD
        - Shared field configuration
        - Error handling
    
    Digunakan oleh:
        - SPDDocumentForm (create)
        - SPDDocumentUpdateForm (update metadata only)
    
    Catatan:
        - SPD forms adalah Form (bukan ModelForm) karena handle 2 models
        - Document model + SPDDocument model
    """
    
    def clean(self):
        """
        Common validation untuk SPD forms
        
        Validates:
            - Date range validation (handled by DateRangeValidationMixin)
            - Destination validation (handled by DestinationFieldMixin)
        
        Returns:
            dict: Cleaned data
        """
        cleaned_data = super().clean()
        
        # Additional SPD-specific validations can be added here
        
        return cleaned_data