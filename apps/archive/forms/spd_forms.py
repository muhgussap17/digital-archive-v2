"""
Modul: forms/spd_forms.py
Fungsi: Forms untuk SPD (Surat Perjalanan Dinas) CRUD operations

Berisi forms:
    - SPDDocumentForm: Create SPD dengan file upload
    - SPDDocumentUpdateForm: Update SPD metadata (no file change)

Implementasi Standar:
    - Menggunakan mixins untuk field definitions
    - Inherit dari BaseSPDForm untuk common logic
    - Minimal code duplication

Catatan Pemeliharaan:
    - SPD forms handle 2 models: Document + SPDDocument
    - SPDDocumentForm untuk CREATE (ada file field)
    - SPDDocumentUpdateForm untuk UPDATE (no file field)
    - Validation logic di mixins dan base class
    
Cara Penggunaan:
    # Create
    form = SPDDocumentForm(request.POST, request.FILES)
    if form.is_valid():
        # Create Document
        spd_category = DocumentCategory.objects.get(slug='spd')
        document = Document.objects.create(
            file=form.cleaned_data['file'],
            document_date=form.cleaned_data['document_date'],
            category=spd_category,
            created_by=request.user
        )
        # Create SPD metadata
        spd = SPDDocument.objects.create(
            document=document,
            employee=form.cleaned_data['employee'],
            destination=form.cleaned_data['destination'],
            ...
        )
    
    # Update
    form = SPDDocumentUpdateForm(data=request.POST)
    if form.is_valid():
        document.document_date = form.cleaned_data['document_date']
        document.save()
        spd.employee = form.cleaned_data['employee']
        spd.save()
"""

from .mixins import (
    DateFieldMixin,
    DateRangeFieldMixin,
    DateRangeValidationMixin,
    FileFieldMixin,
    EmployeeFieldMixin,
    DestinationFieldMixin,
)
from .base import BaseSPDForm


class SPDDocumentForm(
    DateFieldMixin,
    DateRangeFieldMixin,
    DateRangeValidationMixin,
    FileFieldMixin,
    EmployeeFieldMixin,
    DestinationFieldMixin,
    BaseSPDForm
):
    """
    Form untuk CREATE dokumen SPD
    
    Fields (dari mixins):
        - document_date: Tanggal SPD (DateFieldMixin)
        - start_date: Tanggal mulai perjalanan (DateRangeFieldMixin)
        - end_date: Tanggal selesai perjalanan (DateRangeFieldMixin)
        - file: File PDF upload (FileFieldMixin)
        - employee: Pegawai yang melakukan perjalanan (EmployeeFieldMixin)
        - destination: Tujuan perjalanan (DestinationFieldMixin)
        - destination_other: Tujuan lainnya (DestinationFieldMixin)
    
    Validation (dari mixins):
        - document_date tidak boleh masa depan (DateFieldMixin)
        - start_date tidak boleh masa depan (DateRangeValidationMixin)
        - end_date tidak boleh masa depan (DateRangeValidationMixin)
        - end_date >= start_date (DateRangeValidationMixin)
        - File harus PDF valid (FileFieldMixin)
        - destination_other wajib jika destination='other' (DestinationFieldMixin)
    
    Examples:
        >>> form = SPDDocumentForm(data={...}, files={...})
        >>> if form.is_valid():
        ...     # Create Document first
        ...     document = Document.objects.create(...)
        ...     # Then create SPD metadata
        ...     spd = SPDDocument.objects.create(document=document, ...)
    
    Implementasi Standar:
        - Multiple mixins composition
        - All validation logic in mixins
        - Clean separation of concerns
    """
    
    # Override labels if needed
    document_date_label = 'Tanggal SPD'
    document_date_placeholder = 'Pilih tanggal SPD'


class SPDDocumentUpdateForm(
    DateFieldMixin,
    DateRangeFieldMixin,
    DateRangeValidationMixin,
    EmployeeFieldMixin,
    DestinationFieldMixin,
    BaseSPDForm
):
    """
    Form untuk UPDATE dokumen SPD (metadata only)
    
    Fields (dari mixins):
        - document_date: Tanggal SPD (DateFieldMixin)
        - start_date: Tanggal mulai perjalanan (DateRangeFieldMixin)
        - end_date: Tanggal selesai perjalanan (DateRangeFieldMixin)
        - employee: Pegawai yang melakukan perjalanan (EmployeeFieldMixin)
        - destination: Tujuan perjalanan (DestinationFieldMixin)
        - destination_other: Tujuan lainnya (DestinationFieldMixin)
        - NO FILE FIELD (file tidak bisa diubah saat update)
    
    Validation (dari mixins):
        - document_date tidak boleh masa depan (DateFieldMixin)
        - start_date tidak boleh masa depan (DateRangeValidationMixin)
        - end_date tidak boleh masa depan (DateRangeValidationMixin)
        - end_date >= start_date (DateRangeValidationMixin)
        - destination_other wajib jika destination='other' (DestinationFieldMixin)
    
    Notes:
        - File tidak bisa diganti saat update
        - Hanya metadata yang bisa diubah
        - Update affects both Document and SPDDocument models
    
    Examples:
        >>> form = SPDDocumentUpdateForm(data={...})
        >>> if form.is_valid():
        ...     document.document_date = form.cleaned_data['document_date']
        ...     document.save()
        ...     spd.employee = form.cleaned_data['employee']
        ...     spd.destination = form.cleaned_data['destination']
        ...     spd.save()
    
    Implementasi Standar:
        - Tidak include FileFieldMixin (no file change)
        - Reuse all validation dari mixins
    """
    
    # Override labels if needed
    document_date_label = 'Tanggal SPD'
    document_date_placeholder = 'Masukkan Tanggal'