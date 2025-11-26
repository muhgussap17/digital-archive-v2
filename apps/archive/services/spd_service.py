"""
Modul: services/spd_service.py
Fungsi: Business logic untuk SPD (Surat Perjalanan Dinas) operations

Berisi pure business logic untuk:
    - Create SPD document dengan metadata
    - Update SPD metadata
    - Delete SPD (soft delete)

Implementasi Standar:
    - SPD involves 2 models: Document + SPDDocument
    - Transaction management untuk data integrity
    - Pure functions tanpa HTTP dependencies
    - Activity logging untuk audit trail

Catatan Pemeliharaan:
    - SPD create harus create Document DAN SPDDocument dalam 1 transaction
    - Category 'spd' harus sudah exist di database
    - File naming khusus: SPD_[PEGAWAI]_[TUJUAN]_[TANGGAL].pdf
    
Cara Penggunaan:
    from ..services import SPDService
    
    # Create SPD
    document = SPDService.create_spd(
        form_data=form.cleaned_data,
        user=request.user,
        request=request
    )
    
    # Update SPD
    SPDService.update_spd(
        document=document,
        form_data=form.cleaned_data,
        user=request.user
    )
"""

from typing import Dict, Any
from django.db import transaction
from django.utils import timezone

from ..models import Document, DocumentCategory, SPDDocument
from ..utils import (
    rename_document_file,
    relocate_document_file,
    log_document_activity,
)


class SPDService:
    """
    Service class untuk SPD business logic
    
    SPD (Surat Perjalanan Dinas) melibatkan 2 models:
        - Document: File dan metadata umum
        - SPDDocument: Metadata khusus SPD (pegawai, tujuan, tanggal)
    
    Semua operations dalam transaction.atomic untuk ensure
    kedua models tersimpan dengan konsisten.
    """
    
    @staticmethod
    def create_spd(
        form_data: Dict[str, Any],
        user,
        request=None
    ) -> Document:
        """
        Create dokumen SPD baru dengan metadata lengkap
        
        Flow:
            1. Get SPD category
            2. Create Document object
            3. Create SPDDocument metadata
            4. Rename file dengan format SPD khusus
            5. Log activity
        
        Args:
            form_data: Cleaned data dari SPDDocumentForm
                Required keys:
                    - file: Uploaded PDF
                    - document_date: Tanggal SPD
                    - employee: Employee object
                    - destination: Tujuan (choice)
                    - destination_other: Tujuan lainnya (optional)
                    - start_date: Tanggal mulai perjalanan
                    - end_date: Tanggal selesai perjalanan
            user: User yang upload SPD
            request: HttpRequest untuk activity logging (optional)
            
        Returns:
            Document: Created SPD document
            
        Raises:
            DocumentCategory.DoesNotExist: Jika kategori 'spd' tidak ada
            Exception: Jika save gagal (akan di-rollback)
            
        Examples:
            >>> document = SPDService.create_spd(
            ...     form_data={
            ...         'file': uploaded_file,
            ...         'document_date': date(2025, 1, 15),
            ...         'employee': employee_obj,
            ...         'destination': 'jakarta',
            ...         'start_date': date(2025, 1, 15),
            ...         'end_date': date(2025, 1, 17)
            ...     },
            ...     user=request.user,
            ...     request=request
            ... )
        
        Implementasi Standar:
            - Create Document dan SPDDocument dalam 1 transaction
            - Auto assign ke kategori 'spd'
            - File naming: SPD_[PEGAWAI]_[TUJUAN]_[TANGGAL].pdf
        """
        with transaction.atomic():
            # Get SPD category
            spd_category = DocumentCategory.objects.get(slug='spd')
            
            # Create Document
            document = Document.objects.create(
                file=form_data['file'],
                document_date=form_data['document_date'],
                category=spd_category,
                created_by=user
            )
            
            # Create SPD metadata (OneToOne relation)
            spd = SPDDocument.objects.create(
                document=document,
                employee=form_data['employee'],
                destination=form_data['destination'],
                destination_other=form_data.get('destination_other', ''),
                start_date=form_data['start_date'],
                end_date=form_data['end_date']
            )
            
            # Rename file dengan format SPD khusus
            # Format: SPD_[NAMA]_[TUJUAN]_[TANGGAL].pdf
            rename_document_file(document)
            
            # Log activity
            log_document_activity(
                document=document,
                user=user,
                action_type='create',
                description=f'SPD {spd.employee.name} ke {spd.get_destination_display_full()} dibuat',
                request=request
            )
            
            return document
    
    @staticmethod
    def update_spd(
        document: Document,
        form_data: Dict[str, Any],
        user,
        request=None
    ) -> Document:
        """
        Update metadata SPD (tanpa ganti file)
        
        Flow:
            1. Update Document metadata (document_date, version)
            2. Update SPDDocument metadata (employee, destination, dates)
            3. Relocate file jika metadata berubah
            4. Log activity
        
        Args:
            document: Document instance dengan spd_info
            form_data: Cleaned data dari SPDDocumentUpdateForm
                Required keys:
                    - document_date
                    - employee
                    - destination
                    - destination_other (optional)
                    - start_date
                    - end_date
            user: User yang melakukan update
            request: HttpRequest untuk activity logging (optional)
            
        Returns:
            Document: Updated SPD document
            
        Raises:
            AttributeError: Jika document tidak punya spd_info
            Exception: Jika update gagal (akan di-rollback)
            
        Examples:
            >>> updated_doc = SPDService.update_spd(
            ...     document=spd_document,
            ...     form_data={
            ...         'document_date': new_date,
            ...         'employee': new_employee,
            ...         ...
            ...     },
            ...     user=request.user
            ... )
        
        Implementasi Standar:
            - Update Document dan SPDDocument dalam 1 transaction
            - Version increment untuk change tracking
            - Auto rename/relocate file jika pegawai/tujuan berubah
        """
        with transaction.atomic():
            # Update Document metadata
            document.document_date = form_data['document_date']
            document.version += 1
            document.save()
            
            # Update SPD metadata
            spd = document.spd_info # type: ignore
            spd.employee = form_data['employee']
            spd.destination = form_data['destination']
            spd.destination_other = form_data.get('destination_other', '')
            spd.start_date = form_data['start_date']
            spd.end_date = form_data['end_date']
            spd.save()
            
            # Relocate dan rename file jika perlu
            relocate_document_file(document)
            
            # Log activity
            log_document_activity(
                document=document,
                user=user,
                action_type='update',
                description=f'SPD {spd.employee.name} ke {spd.get_destination_display_full()} diperbarui',
                request=request
            )
            
            return document
    
    @staticmethod
    def delete_spd(
        document: Document,
        user,
        request=None
    ) -> Document:
        """
        Soft delete SPD document
        
        Sama seperti delete document biasa, tapi pastikan
        document punya spd_info sebelum delete.
        
        Args:
            document: SPD document instance
            user: User yang melakukan delete
            request: HttpRequest untuk activity logging (optional)
            
        Returns:
            Document: Deleted SPD document
            
        Raises:
            AttributeError: Jika document tidak punya spd_info
            Exception: Jika delete gagal (akan di-rollback)
            
        Examples:
            >>> SPDService.delete_spd(
            ...     document=spd_doc,
            ...     user=request.user
            ... )
        
        Implementasi Standar:
            - Soft delete (is_deleted=True)
            - SPDDocument tetap exist (OneToOne relation)
            - File fisik tidak dihapus
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
                description=f'SPD {document.get_display_name()} dihapus',
                request=request
            )
            
            return document
    
    @staticmethod
    def get_active_spd_documents(filters=None):
        """
        Get active SPD documents dengan optional filters
        
        Helper method untuk query SPD documents.
        
        Args:
            filters: Dictionary of filters (optional)
                Example: {'employee': emp_obj, 'destination': 'jakarta'}
                
        Returns:
            QuerySet: Active SPD documents
        """
        from django.db.models import Q
        
        # Base query: SPD documents only
        queryset = Document.objects.filter(
            is_deleted=False,
            category__slug='spd'
        ).select_related(
            'category',
            'created_by',
            'spd_info__employee'
        )
        
        # Apply filters jika provided
        if filters:
            # Employee filter
            if 'employee' in filters:
                queryset = queryset.filter(
                    spd_info__employee=filters['employee']
                )
            
            # Destination filter
            if 'destination' in filters:
                dest = filters['destination']
                queryset = queryset.filter(
                    Q(spd_info__destination=dest) |
                    Q(spd_info__destination_other__icontains=dest)
                )
            
            # Date range
            if 'date_from' in filters:
                queryset = queryset.filter(
                    document_date__gte=filters['date_from']
                )
            
            if 'date_to' in filters:
                queryset = queryset.filter(
                    document_date__lte=filters['date_to']
                )
            
            # Search
            if 'search' in filters:
                search = filters['search']
                queryset = queryset.filter(
                    Q(spd_info__employee__name__icontains=search) |
                    Q(spd_info__destination__icontains=search) |
                    Q(spd_info__destination_other__icontains=search)
                )
        
        return queryset.order_by('-document_date', '-created_at')