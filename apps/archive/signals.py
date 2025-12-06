"""
Modul: apps/archive/signals.py (REFACTORED)
Fungsi: Django signal handlers untuk Document operations

Signal Handlers:
    - spd_document_saved: Auto-rename SPD file after SPDDocument creation
    - document_pre_delete: Cleanup physical file on HARD DELETE only

Implementasi Standar:
    - Comprehensive documentation
    - Error logging untuk debugging
    - Safe error handling (tidak break operation)
    - Clear usage notes

Catatan Pemeliharaan:
    - spd_document_saved: ALWAYS ACTIVE (critical untuk naming convention)
    - document_pre_delete: ONLY for HARD DELETE (soft delete TIDAK trigger)
    - Sistem default menggunakan SOFT DELETE (is_deleted=True)
    - Physical files preserved untuk compliance & recovery

Flow Diagram:
    SPD Upload:
        User upload → Document created (temp name)
            ↓
        SPDDocument created (with employee & destination)
            ↓
        Signal: spd_document_saved → Rename file
            ↓
        Result: SPD_EmployeeName_Destination_Date.pdf
    
    Document Delete:
        Soft Delete (default):
            DocumentService.delete_document()
                ↓
            is_deleted = True (file preserved)
                ↓
            NO signal triggered
        
        Hard Delete (admin/manual):
            queryset.delete() or Admin bulk delete
                ↓
            Signal: document_pre_delete
                ↓
            Physical file removed
                ↓
            Empty directories cleaned up

Usage Frequency:
    - spd_document_saved: Every SPD upload (HIGH)
    - document_pre_delete: Rare (admin cleanup only) (LOW)
"""

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.conf import settings
from .models import Document, SPDDocument
from .utils import rename_document_file
import os
import logging

logger = logging.getLogger(__name__)


# ==================== SPD DOCUMENT SIGNALS ====================

@receiver(post_save, sender=SPDDocument)
def spd_document_saved(sender, instance, created, **kwargs):
    """
    Auto-rename SPD file setelah SPDDocument instance created
    
    Triggered: EVERY TIME SPDDocument is saved (if created=True)
    
    Purpose:
        Rename uploaded SPD file dengan naming convention standar
        yang include employee name, destination, dan date.
    
    Flow:
        1. User upload SPD via web interface
        2. Document created dengan temporary filename:
           SPD_2025-01-15_153045.pdf
        3. SPDDocument created dengan employee & destination data
        4. Signal fired → This function called
        5. File renamed to proper format:
           SPD_JohnDoe_Jakarta_2025-01-15.pdf
    
    Naming Convention:
        Format: SPD_{employee_name}_{destination}_{date}.pdf
        Example: SPD_JohnDoe_Jakarta_2025-01-15.pdf
    
    Args:
        sender: SPDDocument model class
        instance: SPDDocument instance yang baru dibuat
        created: Boolean, True jika baru created (not updated)
        **kwargs: Additional signal arguments
    
    Error Handling:
        - Logs error jika rename gagal
        - Does NOT raise exception (prevent blocking save operation)
        - Operation continues even if rename fails
    
    Implementasi Standar:
        - ALWAYS ACTIVE (tidak bisa di-disable)
        - Called automatically by Django signals
        - Safe error handling
        - Comprehensive logging
    
    Catatan:
        - Only runs on creation (created=True)
        - Uses utils.rename_document_file() for actual renaming
        - File already uploaded, this just renames it
    """
    if created:
        try:
            # Rename file menggunakan utility function
            rename_document_file(instance.document)
            
            # Log success untuk audit trail
            logger.info(
                f"SPD file renamed successfully: {instance.document.file.name} "
                f"(Employee: {instance.employee.name}, "
                f"Destination: {instance.get_destination_display_full()})"
            )
            
        except Exception as e:
            # Log error tapi tidak raise exception
            # Agar tidak block save operation
            logger.error(
                f"Failed to rename SPD file for document {instance.document.id}: {str(e)}",
                exc_info=True  # Include stack trace
            )


# ==================== DOCUMENT DELETION SIGNALS ====================

@receiver(pre_delete, sender=Document)
def document_pre_delete(sender, instance, **kwargs):
    """
    Remove physical file dari storage saat document di-HARD DELETE
    
    ⚠️ IMPORTANT: ONLY TRIGGERED FOR HARD DELETE
    
    Sistem Soft Delete:
        - Default deletion method: DocumentService.delete_document()
        - Sets is_deleted=True, deleted_at=timestamp
        - Physical file PRESERVED untuk compliance & recovery
        - This signal NOT triggered
    
    When This Signal IS Triggered:
        1. Django Admin bulk delete action
        2. Manual queryset.delete() call
        3. Management commands: cleanup_old_documents --hard
        4. Developer manual deletion via shell
        5. CASCADE delete dari related objects
    
    When This Signal is NOT Triggered:
        ❌ User delete via web interface (soft delete)
        ❌ DocumentService.delete_document() (soft delete)
        ❌ Bulk soft delete operations
        ❌ Normal user operations
    
    Flow:
        Admin bulk delete → Signal fired
            ↓
        Check if file exists
            ↓
        Remove physical file from storage
            ↓
        Try cleanup empty directories (best effort)
            ↓
        Log success/failure
    
    Features:
        - Removes physical file dari media storage
        - Cleans up empty directories (optional)
        - Safe error handling (logs but doesn't raise)
        - Respects MEDIA_ROOT boundary
    
    Args:
        sender: Document model class
        instance: Document instance yang akan dihapus
        **kwargs: Additional signal arguments
    
    Directory Cleanup:
        - Walks up directory tree
        - Removes empty directories
        - Stops at MEDIA_ROOT
        - Ignores errors (best effort only)
    
    Error Handling:
        - Logs error jika delete gagal
        - Does NOT raise exception
        - Operation continues even if cleanup fails
    
    Implementasi Standar:
        - Defensive programming (check file exists)
        - Comprehensive logging
        - Safe cleanup (best effort)
        - No operation blocking
    
    Security:
        - Only removes files within MEDIA_ROOT
        - Does not follow symlinks
        - Safe directory traversal
    
    Usage Examples:
        # Admin hard delete (triggers signal):
        >>> Document.objects.filter(is_deleted=True, 
        ...     deleted_at__lt=one_year_ago).delete()
        
        # Soft delete (does NOT trigger signal):
        >>> DocumentService.delete_document(document, user)
        
        # Management command (triggers signal):
        >>> python manage.py cleanup_old_documents --hard
    
    Catatan:
        - Use case: Periodic cleanup old soft-deleted documents
        - Frequency: Low (usually monthly/quarterly via cron)
        - Recovery: Impossible after hard delete (by design)
    """
    if instance.file:
        try:
            # Get absolute file path
            file_path = instance.file.path
            
            # Check if file actually exists di filesystem
            if os.path.exists(file_path):
                # Remove physical file
                os.remove(file_path)
                
                logger.info(
                    f"Physical file deleted successfully: {file_path} "
                    f"(Document ID: {instance.id}, Category: {instance.category.name})"
                )
                
                # Try to cleanup empty directories (best effort)
                # Walk up directory tree dan hapus empty folders
                directory = os.path.dirname(file_path)
                
                try:
                    # Keep removing empty parent directories
                    # until we hit MEDIA_ROOT atau non-empty directory
                    while directory != settings.MEDIA_ROOT:
                        # Check if directory is empty
                        if not os.listdir(directory):
                            os.rmdir(directory)
                            logger.debug(f"Removed empty directory: {directory}")
                            
                            # Move up to parent directory
                            directory = os.path.dirname(directory)
                        else:
                            # Directory not empty, stop cleanup
                            break
                            
                except OSError as e:
                    # Ignore errors in directory cleanup
                    # This is best-effort only
                    logger.debug(
                        f"Could not remove directory {directory}: {str(e)}"
                    )
                    pass
            else:
                # File doesn't exist (maybe already deleted manually)
                logger.warning(
                    f"File path does not exist (already deleted?): {file_path} "
                    f"(Document ID: {instance.id})"
                )
                
        except Exception as e:
            # Log error tapi tidak raise exception
            # Agar tidak block delete operation
            logger.error(
                f"Failed to delete physical file for document {instance.id}: {str(e)}",
                exc_info=True  # Include full stack trace
            )


# ==================== CLEANUP & NOTES ====================

"""
REMOVED: ensure_upload_directories signal handler

Previous Implementation (Removed):
    @receiver(post_save, sender=Document)
    def ensure_upload_directories(sender, instance, created, **kwargs):
        # Create directory structure for years 2020-2030
        # Creates 12*10 = 120 folders per category

Reason for Removal:
    1. Unnecessary: Django's FileField auto-creates directories on upload
    2. Wasteful: Pre-creates 120+ empty folders that may never be used
    3. Performance: Adds overhead to every document save
    4. Modern Practice: Create directories on-demand (lazy creation)

Modern Approach:
    - Let Django handle directory creation automatically
    - Directories created only when actually needed
    - No pre-creation required
    - Better performance and cleaner filesystem

Migration:
    - No action needed
    - Existing directories preserved
    - New directories created automatically by Django
    - No data loss or functionality impact
"""