import os
import re
from django.conf import settings
from django.utils.text import slugify
from .models import DocumentActivity
from datetime import datetime


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_user_agent(request):
    """Get user agent from request"""
    return request.META.get('HTTP_USER_AGENT', '')


def log_activity(document, user, action_type, description=None, request=None):
    """
    Log document activity
    
    Args:
        document: Document instance
        user: User instance
        action_type: One of: 'create', 'view', 'download', 'update', 'delete'
        description: Optional description
        request: HttpRequest object (optional, for IP/User-Agent)
    """
    activity_data = {
        'document': document,
        'user': user,
        'action_type': action_type,
        'description': description or '',
    }
    
    if request:
        activity_data['ip_address'] = get_client_ip(request)
        activity_data['user_agent'] = get_user_agent(request)
    
    return DocumentActivity.objects.create(**activity_data)


def generate_spd_filename(spd_document):
    """
    Generate standardized filename for SPD document
    Format: SPD_EmployeeName_Destination_YYYY-MM-DD.pdf
    
    Args:
        spd_document: SPDDocument instance
        
    Returns:
        str: Generated filename
    """
    document = spd_document.document
    
    # Clean employee name - PRESERVE CASE, only remove spaces & special chars
    employee_name = spd_document.employee.name
    # Remove special characters but keep spaces
    employee_name = re.sub(r'[^\w\s-]', '', employee_name)
    # Remove spaces (join words without separator)
    employee_name = re.sub(r'\s+', '', employee_name)
    
    # Clean destination
    destination = spd_document.get_destination_display_full()
    destination_clean = re.sub(r'[^\w\s-]', '', destination)
    destination_clean = re.sub(r'\s+', '', destination_clean)

    # Date in YYYY-MM-DD format
    date_str = document.document_date.strftime('%Y-%m-%d')
    
    # Construct filename
    filename = f"SPD_{employee_name}_{destination_clean}_{date_str}.pdf"
    
    return filename


def generate_belanjaan_filename(document):
    """
    Generate standardized filename for Belanjaan document
    Format: SubCategory_YYYY-MM-DD.pdf
    
    Args:
        document: Document instance
        
    Returns:
        str: Generated filename
    """
    # Get subcategory name
    category = document.category
    category_name = category.name if category.parent else category.slug
    
    # Clean category name - PRESERVE CASE
    category_clean = re.sub(r'[^\w\s-]', '', category_name)
    category_clean = re.sub(r'\s+', '', category_clean)
    
    # Date in YYYY-MM-DD format
    date_str = document.document_date.strftime('%Y-%m-%d')
    
    # Construct filename
    filename = f"{category_clean}_{date_str}.pdf"
    
    return filename


# def get_unique_filename(directory, filename):
#     """
#     Generate unique filename if file already exists
#     Adds suffix _1, _2, etc.
    
#     Args:
#         directory: Directory path
#         filename: Base filename
        
#     Returns:
#         str: Unique filename
#     """
#     full_path = os.path.join(directory, filename)
    
#     if not os.path.exists(full_path):
#         return filename
    
#     name, ext = os.path.splitext(filename)
#     counter = 1
    
#     while True:
#         new_filename = f"{name}_{counter}{ext}"
#         new_path = os.path.join(directory, new_filename)
        
#         if not os.path.exists(new_path):
#             return new_filename
        
#         counter += 1


def get_unique_filepath(filepath):
    """
    Generate unique filepath if file already exists
    Adds suffix _1, _2, etc.
    """
    if not os.path.exists(filepath):
        return filepath
    
    directory = os.path.dirname(filepath)
    filename = os.path.basename(filepath)
    name, ext = os.path.splitext(filename)
    counter = 1
    
    while True:
        new_filename = f"{name}_{counter}{ext}"
        new_filepath = os.path.join(directory, new_filename)
        
        if not os.path.exists(new_filepath):
            return new_filepath
        
        counter += 1


def rename_document_file(document, new_filename=None):
    """
    Rename document file with proper format
    
    Args:
        document: Document instance
        new_filename: Optional custom filename (will generate if not provided)
    
    Returns:
        str: New file path
    """
    if not document.file:
        return None
    
    category = document.category
    
    # Only rename SPD (after spd_info is available)
    if category.slug == 'spd' or (category.parent and category.parent.slug == 'spd'):
        try:
            spd_info = document.spd_info
            
            # Generate new filename with employee name
            if not new_filename:
                new_filename = generate_spd_filename(spd_info)
            
            old_path = document.file.path
            
            # Build new path (same directory, different name)
            directory = os.path.dirname(old_path)
            new_path = os.path.join(directory, new_filename)
            
            # Rename physical file if different
            if old_path != new_path and os.path.exists(old_path):
                # Ensure unique filename
                new_path = get_unique_filepath(new_path)
                new_filename = os.path.basename(new_path)
                
                os.rename(old_path, new_path)
                
                # Update database with new filename
                year = document.document_date.strftime('%Y')
                month = document.document_date.strftime('%m-%B')
                category_path = document.category.get_full_path()
                
                new_relative_path = os.path.join(
                    'uploads',
                    category_path,
                    year,
                    month,
                    new_filename
                )
                
                document.file.name = new_relative_path
                document.save(update_fields=['file'])
                
                return new_relative_path
        except:
            # SPD info not available yet, skip rename
            pass
    
    # For Belanjaan, do nothing (already named correctly by upload_path)
    return None


def format_file_size(size_bytes):
    """
    Format file size to human readable format
    
    Args:
        size_bytes: File size in bytes
        
    Returns:
        str: Formatted size (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def validate_pdf_file(file):
    """
    Validate uploaded file is a valid PDF
    
    Args:
        file: UploadedFile instance
        
    Returns:
        tuple: (is_valid, error_message)
    """
    # Check extension
    ext = os.path.splitext(file.name)[1].lower()
    if ext != '.pdf':
        return False, "File harus berformat PDF"
    
    # Check file size (max 10MB)
    max_size = 10 * 1024 * 1024  # 10MB
    if file.size > max_size:
        return False, f"Ukuran file maksimal {format_file_size(max_size)}"
    
    # Check PDF signature (magic bytes)
    file.seek(0)
    header = file.read(4)
    file.seek(0)
    
    if header != b'%PDF':
        return False, "File bukan PDF yang valid"
    
    return True, None