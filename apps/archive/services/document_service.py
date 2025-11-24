"""
Modul: services/document_service.py
Fungsi: Business logic untuk Document operations

Berisi pure business logic untuk:
    - Create document
    - Update document
    - Delete document (soft delete)
    - File operations

Implementasi Standar:
    - Separation of concerns: business logic terpisah dari HTTP handling
    - Transaction management di service layer
    - Pure functions yang mudah di-test
    - No HTTP dependencies (request, messages, redirect)

Catatan Pemeliharaan:
    - Service functions harus pure (no side effects di HTTP layer)
    - Semua file operations melalui utils
    - Activity logging wajib untuk audit trail
    - Transaction atomic untuk data integrity
    
Cara Penggunaan:
    from ..services import DocumentService
    
    # Create
    document = DocumentService.create_document(
        form_data=form.cleaned_data,
        file=request.FILES.get('file'),
        user=request.user,
        request=request  # Optional, for activity logging
    )
    
    # Update
    updated_doc = DocumentService.update_document(
        document=document,
        form_data=form.cleaned_data,
        user=request.user,
        request=request
    )
    
    # Delete
    DocumentService.delete_document(
        document=document,
        user=request.user,
        request=request
    )
"""

from typing import Dict, Any, Optional
from django.db import transaction
from django.utils import timezone

from ..models import Document, DocumentCategory
from ..utils import (
    rename_document_file,
    relocate_document_file,
    log_document_activity,
)


class DocumentService:
    """
    Service class untuk Document business logic
    
    Menyediakan static methods untuk:
        - create_document: Create dokumen baru dengan file
        - update_document: Update metadata dokumen
        - delete_document: Soft delete dokumen
    
    Semua methods menggunakan transaction.atomic untuk data integrity
    dan automatic rollback jika terjadi error.
    """
    
    @staticmethod
    def create_document(
        form_data: Dict[str, Any],
        file,
        user,
        request=None
    ) -> Document:
        """
        Create dokumen baru dengan file upload
        
        Flow:
            1. Create Document object
            2. Assign user yang upload
            3. Rename file sesuai standar
            4. Log activity untuk audit
        
        Args:
            form_data: Cleaned data dari DocumentForm
                Required keys: category, document_date
            file: Uploaded file object
            user: User yang melakukan upload
            request: HttpRequest untuk activity logging (optional)
            
        Returns:
            Document: Created document instance
            
        Raises:
            Exception: Jika save gagal (akan di-rollback)
            
        Examples:
            >>> document = DocumentService.create_document(
            ...     form_data={
            ...         'category': category_obj,
            ...         'document_date': date(2024, 1, 15)
            ...     },
            ...     file=uploaded_file,
            ...     user=request.user,
            ...     request=request
            ... )
        
        Implementasi Standar:
            - Menggunakan transaction.atomic untuk rollback safety
            - Auto rename file sesuai naming convention
            - Activity logging untuk compliance
        """
        with transaction.atomic():
            # Create document instance
            document = Document.objects.create(
                file=file,
                document_date=form_data['document_date'],
                category=form_data['category'],
                created_by=user
            )
            
            # Rename file sesuai standar naming
            # Format: [KATEGORI]_[TANGGAL].pdf
            rename_document_file(document)
            
            # Log activity untuk audit trail
            log_document_activity(
                document=document,
                user=user,
                action_type='create',
                description=f'Dokumen {document.get_display_name()} dibuat',
                request=request
            )
            
            return document
    
    @staticmethod
    def update_document(
        document: Document,
        form_data: Dict[str, Any],
        user,
        request=None
    ) -> Document:
        """
        Update metadata dokumen (tanpa ganti file)
        
        Flow:
            1. Update category dan document_date
            2. Increment version number
            3. Move file jika kategori/tanggal berubah
            4. Log activity
        
        Args:
            document: Document instance yang akan diupdate
            form_data: Cleaned data dari DocumentUpdateForm
                Required keys: category, document_date
            user: User yang melakukan update
            request: HttpRequest untuk activity logging (optional)
            
        Returns:
            Document: Updated document instance
            
        Raises:
            Exception: Jika update gagal (akan di-rollback)
            
        Examples:
            >>> updated_doc = DocumentService.update_document(
            ...     document=doc,
            ...     form_data={
            ...         'category': new_category,
            ...         'document_date': new_date
            ...     },
            ...     user=request.user,
            ...     request=request
            ... )
        
        Implementasi Standar:
            - Version increment untuk change tracking
            - Auto relocate file jika folder structure berubah
            - Activity logging untuk audit
        
        Catatan:
            - File tidak bisa diganti, hanya metadata
            - Jika kategori berubah, file dipindah ke folder baru
        """
        with transaction.atomic():
            # Update metadata
            document.category = form_data['category']
            document.document_date = form_data['document_date']
            document.version += 1  # Track changes
            document.save()
            
            # Move file jika kategori/tanggal berubah
            # File akan dipindah ke folder yang sesuai
            relocate_document_file(document)
            
            # Log activity
            log_document_activity(
                document=document,
                user=user,
                action_type='update',
                description=f'Dokumen {document.get_display_name()} diperbarui',
                request=request
            )
            
            return document
    
    @staticmethod
    def delete_document(
        document: Document,
        user,
        request=None
    ) -> Document:
        """
        Soft delete dokumen
        
        Menandai dokumen sebagai deleted tanpa menghapus dari database.
        File fisik tidak dihapus untuk compliance dan recovery.
        
        Args:
            document: Document instance yang akan dihapus
            user: User yang melakukan delete
            request: HttpRequest untuk activity logging (optional)
            
        Returns:
            Document: Deleted document instance
            
        Raises:
            Exception: Jika delete gagal (akan di-rollback)
            
        Examples:
            >>> DocumentService.delete_document(
            ...     document=doc,
            ...     user=request.user,
            ...     request=request
            ... )
        
        Implementasi Standar:
            - Soft delete sesuai data retention policy
            - File fisik tetap tersimpan untuk recovery
            - Activity logging untuk audit
        
        Catatan:
            - is_deleted = True, deleted_at = timestamp
            - File bisa di-restore dengan set is_deleted=False
            - Untuk hard delete, gunakan cronjob terpisah
        """
        with transaction.atomic():
            # Set soft delete flags
            document.is_deleted = True
            document.deleted_at = timezone.now()
            document.save()
            
            # Log activity
            log_document_activity(
                document=document,
                user=user,
                action_type='delete',
                description=f'Dokumen {document.get_display_name()} dihapus',
                request=request
            )
            
            return document
    
    @staticmethod
    def get_active_documents(filters: Optional[Dict[str, Any]] = None):
        """
        Get active documents dengan optional filters
        
        Helper method untuk query documents dengan optimization.
        
        Args:
            filters: Dictionary of filters (optional)
                Example: {'category': cat_obj, 'date_from': date}
                
        Returns:
            QuerySet: Active documents
            
        Examples:
            >>> docs = DocumentService.get_active_documents({
            ...     'category': category,
            ...     'date_from': date(2024, 1, 1)
            ... })
        """
        from django.db.models import Q
        
        # Base query: active documents only
        queryset = Document.objects.filter(
            is_deleted=False
        ).select_related(
            'category',
            'category__parent',
            'created_by'
        )
        
        # Apply filters jika provided
        if filters:
            # Category filter
            if 'category' in filters:
                category = filters['category']
                category_ids = [category.id]
                
                # Include child categories
                if category.children.exists():
                    category_ids.extend(
                        category.children.values_list('id', flat=True)
                    )
                
                queryset = queryset.filter(category_id__in=category_ids)
            
            # Date range filters
            if 'date_from' in filters:
                queryset = queryset.filter(
                    document_date__gte=filters['date_from']
                )
            
            if 'date_to' in filters:
                queryset = queryset.filter(
                    document_date__lte=filters['date_to']
                )
            
            # Search filter
            if 'search' in filters:
                search = filters['search']
                queryset = queryset.filter(
                    Q(category__name__icontains=search) |
                    Q(file__icontains=search)
                )
        
        return queryset.order_by('-document_date', '-created_at')