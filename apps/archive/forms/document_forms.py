"""
Modul: forms/document_forms.py
Fungsi: Forms untuk Document (Belanjaan) CRUD operations

Berisi forms:
    - DocumentForm: Create document dengan file upload
    - DocumentUpdateForm: Update document metadata (no file change)

Implementasi Standar:
    - Menggunakan mixins untuk field definitions
    - Inherit dari BaseDocumentForm untuk common logic
    - Minimal code duplication

Catatan Pemeliharaan:
    - DocumentForm untuk CREATE (ada file field)
    - DocumentUpdateForm untuk UPDATE (no file field)
    - Validation logic di mixins dan base class
    
Cara Penggunaan:
    # Create
    form = DocumentForm(request.POST, request.FILES)
    if form.is_valid():
        document = form.save(commit=False)
        document.created_by = request.user
        document.save()
    
    # Update
    form = DocumentUpdateForm(request.POST, instance=document)
    if form.is_valid():
        form.save()
"""

from ..models import Document
from .mixins import CategoryFieldMixin, DateFieldMixin, FileFieldMixin
from .base import BaseDocumentForm


class DocumentForm(CategoryFieldMixin, DateFieldMixin, FileFieldMixin, BaseDocumentForm):
    """
    Form untuk CREATE dokumen belanjaan
    
    Fields (dari mixins):
        - category: Kategori dokumen (CategoryFieldMixin)
        - document_date: Tanggal dokumen (DateFieldMixin)
        - file: File PDF upload (FileFieldMixin)
    
    Validation (dari mixins):
        - Category tidak boleh SPD (CategoryFieldMixin)
        - Document date tidak boleh masa depan (DateFieldMixin)
        - File harus PDF valid (FileFieldMixin)
    
    Examples:
        >>> form = DocumentForm(data={...}, files={...})
        >>> if form.is_valid():
        ...     document = form.save(commit=False)
        ...     document.created_by = request.user
        ...     document.save()
    
    Implementasi Standar:
        - Menggunakan mixins untuk DRY principle
        - Validation logic terisolasi di mixins
        - Clean separation of concerns
    """
    
    class Meta: # type: ignore
        model = Document
        fields = ['category', 'document_date', 'file']


class DocumentUpdateForm(CategoryFieldMixin, DateFieldMixin, BaseDocumentForm):
    """
    Form untuk UPDATE dokumen belanjaan (metadata only)
    
    Fields (dari mixins):
        - category: Kategori dokumen (CategoryFieldMixin)
        - document_date: Tanggal dokumen (DateFieldMixin)
        - NO FILE FIELD (file tidak bisa diubah saat update)
    
    Validation (dari mixins):
        - Category tidak boleh SPD (CategoryFieldMixin)
        - Document date tidak boleh masa depan (DateFieldMixin)
    
    Notes:
        - File tidak bisa diganti saat update
        - Hanya metadata yang bisa diubah
        - Jika perlu ganti file, harus delete dan create baru
    
    Examples:
        >>> form = DocumentUpdateForm(data={...}, instance=document)
        >>> if form.is_valid():
        ...     updated_document = form.save()
    
    Implementasi Standar:
        - Tidak include FileFieldMixin (no file change)
        - Reuse validation dari mixins
    """
    
    class Meta: # type: ignore
        model = Document
        fields = ['category', 'document_date']  # NO FILE!