from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.conf import settings
from .models import Document, SPDDocument
from .utils import rename_document_file, log_document_activity
import os
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=SPDDocument)
def spd_document_saved(sender, instance, created, **kwargs):
    """
    After SPD document is saved, rename the file with complete information
    """
    if created:
        try:
            # Rename file with employee and destination info
            rename_document_file(instance.document)
            logger.info(f"SPD document file renamed: {instance.document.file.name}")
        except Exception as e:
            logger.error(f"Failed to rename SPD file: {str(e)}")


@receiver(pre_delete, sender=Document)
def document_pre_delete(sender, instance, **kwargs):
    """
    Before document is permanently deleted, remove the physical file
    """
    if instance.file:
        try:
            file_path = instance.file.path
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Physical file deleted: {file_path}")
                
                # Try to remove empty directories
                directory = os.path.dirname(file_path)
                try:
                    while directory != settings.MEDIA_ROOT:
                        if not os.listdir(directory):
                            os.rmdir(directory)
                            directory = os.path.dirname(directory)
                        else:
                            break
                except:
                    pass  # Ignore errors in cleanup
                    
        except Exception as e:
            logger.error(f"Failed to delete physical file: {str(e)}")


# @receiver(post_save, sender=Document)
# def ensure_upload_directories(sender, instance, created, **kwargs):
#     """
#     Ensure upload directories exist for the category
#     """
#     if created and instance.category:
#         try:
#             category_path = instance.category.get_full_path()
#             years = range(2020, 2030)  # Prepare directories for common years
            
#             for year in years:
#                 for month in range(1, 13):
#                     month_name = {
#                         1: '01-January', 2: '02-February', 3: '03-March',
#                         4: '04-April', 5: '05-May', 6: '06-June',
#                         7: '07-July', 8: '08-August', 9: '09-September',
#                         10: '10-October', 11: '11-November', 12: '12-December'
#                     }[month]
                    
#                     directory = os.path.join(
#                         settings.MEDIA_ROOT,
#                         'uploads',
#                         category_path,
#                         str(year),
#                         month_name
#                     )
                    
#                     os.makedirs(directory, exist_ok=True)
#         except Exception as e:
#             logger.error(f"Failed to create upload directories: {str(e)}")