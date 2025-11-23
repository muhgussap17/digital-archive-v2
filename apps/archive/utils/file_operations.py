"""
Modul: utils/file_operations.py
Fungsi: File handling operations untuk document management

Berisi fungsi-fungsi untuk:
    - Validasi file upload (PDF validation)
    - Generate filename dengan standar naming convention
    - Rename dan relocate file berdasarkan metadata
    - Ensure unique filepath untuk prevent overwrite

Implementasi Standar:
    - Mengikuti PEP 8 naming conventions
    - Type hints untuk semua fungsi
    - Comprehensive docstrings dengan contoh penggunaan
    - Menggunakan constants dari constants.py
    - Error handling yang proper

Catatan Pemeliharaan:
    - Semua file operations harus melalui fungsi di module ini
    - Jangan hardcode filename format, gunakan constants
    - Preserve case sensitivity untuk nama (employee, category)
    - Selalu check file existence sebelum operasi
    
Dependencies:
    - apps.archive.constants: File operation constants
    - apps.archive.models: Document, SPDDocument models
    - Django settings: MEDIA_ROOT
"""

import os
import re
import shutil
from typing import Optional, Tuple
from django.conf import settings

from ..constants import (
    MAX_FILE_SIZE,
    PDF_FILE_SIGNATURE,
    ALLOWED_FILE_EXTENSIONS,
    ERROR_INVALID_EXTENSION,
    ERROR_FILE_TOO_LARGE,
    ERROR_INVALID_PDF,
    FILENAME_CLEAN_PATTERN,
    FILENAME_SPACES_PATTERN,
    FILENAME_DATE_FORMAT,
    DateFormat,
    FilePathBuilder,
)


# ==================== PRIVATE HELPER FUNCTIONS ====================

def _clean_filename(text: str) -> str:
    """
    Clean text untuk digunakan sebagai filename
    
    Menghapus special characters tapi PRESERVE CASE.
    Hanya remove spaces dan karakter yang tidak aman untuk filename.
    
    Args:
        text: Text yang akan dibersihkan
        
    Returns:
        Cleaned text (e.g., "John Doe" -> "JohnDoe")
        
    Examples:
        >>> _clean_filename("John Doe")
        'JohnDoe'
        >>> _clean_filename("ATK & Alat Tulis")
        'ATKAlatTulis'
    
    Implementasi Standar:
        - Menggunakan regex pattern dari constants
        - Preserve case untuk consistency
    """
    # Remove special characters (keep alphanumeric, spaces, hyphens)
    cleaned = re.sub(FILENAME_CLEAN_PATTERN, '', text)
    
    # Remove multiple spaces/hyphens
    cleaned = re.sub(FILENAME_SPACES_PATTERN, '', cleaned)
    
    return cleaned


def _get_file_extension(filename: str) -> str:
    """
    Extract file extension dengan aman
    
    Args:
        filename: Nama file
        
    Returns:
        Extension dengan dot (e.g., ".pdf")
        Fallback ke ".pdf" jika tidak ada extension
        
    Examples:
        >>> _get_file_extension("document.pdf")
        '.pdf'
        >>> _get_file_extension("document")
        '.pdf'
    """
    _, ext = os.path.splitext(filename)
    return ext if ext else '.pdf'


# ==================== FILE VALIDATION ====================

def validate_pdf_file(file) -> Tuple[bool, Optional[str]]:
    """
    Validasi file upload adalah PDF yang valid
    
    Melakukan 3 level validasi:
        1. Extension check (.pdf)
        2. File size check (max 10MB)
        3. Magic bytes check (PDF signature)
    
    Args:
        file: Django UploadedFile instance
        
    Returns:
        Tuple (is_valid, error_message)
            - is_valid: True jika valid, False jika tidak
            - error_message: None jika valid, string error jika tidak
            
    Examples:
        >>> from django.core.files.uploadedfile import SimpleUploadedFile
        >>> pdf_file = SimpleUploadedFile("test.pdf", b"%PDF-1.4...")
        >>> is_valid, error = validate_pdf_file(pdf_file)
        >>> print(is_valid)
        True
        
    Implementasi Standar:
        - Sesuai dengan security best practices untuk file upload
        - Menggunakan constants untuk configuration
        - Reset file pointer setelah read
        
    Catatan Pemeliharaan:
        - Jika perlu support format lain, update ALLOWED_FILE_EXTENSIONS
        - Jika perlu ubah max size, update MAX_FILE_SIZE constant
    """
    # Validation 1: Check extension
    ext = os.path.splitext(file.name)[1].lower().lstrip('.')
    if ext not in ALLOWED_FILE_EXTENSIONS:
        return False, ERROR_INVALID_EXTENSION
    
    # Validation 2: Check file size
    if file.size > MAX_FILE_SIZE:
        from .formatters import format_file_size
        max_size_display = format_file_size(MAX_FILE_SIZE)
        return False, ERROR_FILE_TOO_LARGE.format(max_size=max_size_display)
    
    # Validation 3: Check PDF signature (magic bytes)
    file.seek(0)
    header = file.read(4)
    file.seek(0)  # Reset pointer
    
    if header != PDF_FILE_SIGNATURE:
        return False, ERROR_INVALID_PDF
    
    return True, None


# ==================== FILENAME GENERATION ====================

def generate_spd_filename(spd_document) -> str:
    """
    Generate filename standar untuk dokumen SPD
    
    Format: SPD_NamaPegawai_Tujuan_YYYY-MM-DD.pdf
    
    Args:
        spd_document: SPDDocument instance
        
    Returns:
        Generated filename string
        
    Examples:
        >>> # Assuming spd_document with:
        >>> # employee.name = "John Doe"
        >>> # destination = "Jakarta"
        >>> # document_date = 2024-01-15
        >>> filename = generate_spd_filename(spd_document)
        >>> print(filename)
        SPD_JohnDoe_Jakarta_2024-01-15.pdf
    
    Implementasi Standar:
        - Preserve case untuk nama pegawai dan tujuan
        - Format tanggal ISO (YYYY-MM-DD)
        - Remove special characters tapi keep readability
        
    Catatan Pemeliharaan:
        - Jika format berubah, update SPD_FILENAME_FORMAT constant
        - Clean filename preserve case untuk professional appearance
    """
    document = spd_document.document
    
    # Clean employee name (preserve case)
    employee_name = _clean_filename(spd_document.employee.name)
    
    # Clean destination
    destination = spd_document.get_destination_display_full()
    destination_clean = _clean_filename(destination)
    
    # Format date
    date_str = document.document_date.strftime(FILENAME_DATE_FORMAT)
    
    # Construct filename
    filename = f"SPD_{employee_name}_{destination_clean}_{date_str}.pdf"
    
    return filename


def generate_document_filename(document) -> str:
    """
    Generate filename standar untuk dokumen belanjaan
    
    Format: Kategori_YYYY-MM-DD.pdf
    
    Args:
        document: Document instance
        
    Returns:
        Generated filename string
        
    Examples:
        >>> # Assuming document with:
        >>> # category.name = "ATK"
        >>> # document_date = 2024-01-15
        >>> filename = generate_document_filename(document)
        >>> print(filename)
        ATK_2024-01-15.pdf
    
    Implementasi Standar:
        - Gunakan subcategory name (bukan parent)
        - Preserve case untuk category name
        - Format tanggal ISO (YYYY-MM-DD)
        
    Catatan Pemeliharaan:
        - Untuk kategori dengan parent, gunakan child name
        - Clean category name preserve case
    """
    # Get subcategory name
    category = document.category
    category_name = category.name if category.parent else category.slug
    
    # Clean category name (preserve case)
    category_clean = _clean_filename(category_name)
    
    # Format date
    date_str = document.document_date.strftime(FILENAME_DATE_FORMAT)
    
    # Construct filename
    filename = f"{category_clean}_{date_str}.pdf"
    
    return filename


# ==================== FILE PATH OPERATIONS ====================

def ensure_unique_filepath(filepath: str) -> str:
    """
    Generate unique filepath jika file sudah ada
    
    Menambahkan suffix _1, _2, dst jika file dengan nama sama sudah ada.
    Berguna untuk prevent overwrite file yang sudah ada.
    
    Args:
        filepath: Full path ke file yang diinginkan
        
    Returns:
        Unique filepath (original atau dengan suffix)
        
    Examples:
        >>> # Jika file tidak exist
        >>> path = ensure_unique_filepath("/media/uploads/ATK_2024-01-15.pdf")
        >>> print(path)
        /media/uploads/ATK_2024-01-15.pdf
        
        >>> # Jika file exist
        >>> path = ensure_unique_filepath("/media/uploads/ATK_2024-01-15.pdf")
        >>> print(path)
        /media/uploads/ATK_2024-01-15_1.pdf
    
    Implementasi Standar:
        - Iterative check untuk find available name
        - Preserve extension
        - Suffix sebelum extension
        
    Catatan Pemeliharaan:
        - Jika perlu custom suffix format, update logic di sini
        - Consider race condition untuk concurrent uploads
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


# ==================== FILE RENAME & RELOCATE ====================

def rename_document_file(document, new_filename: Optional[str] = None) -> Optional[str]:
    """
    Rename file dokumen dengan format yang benar
    
    Fungsi ini dipanggil setelah SPDDocument dibuat untuk rename file
    dengan informasi lengkap (employee name, destination).
    
    Args:
        document: Document instance
        new_filename: Optional custom filename (auto-generate jika None)
        
    Returns:
        New relative file path jika berhasil, None jika tidak perlu rename
        
    Examples:
        >>> # After creating SPD document
        >>> new_path = rename_document_file(document)
        >>> print(new_path)
        uploads/spd/2024/01-Januari/SPD_JohnDoe_Jakarta_2024-01-15.pdf
    
    Implementasi Standar:
        - Hanya rename SPD files (after spd_info available)
        - Belanjaan files sudah benar dari document_upload_path
        - Update database dengan path baru
        - Handle file yang sudah exist dengan ensure_unique_filepath
        
    Catatan Pemeliharaan:
        - Dipanggil dari signal post_save SPDDocument
        - Jangan panggil manual untuk belanjaan documents
        - Ensure directory exist sebelum rename
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
                new_path = ensure_unique_filepath(new_path)
                new_filename = os.path.basename(new_path)
                
                os.rename(old_path, new_path)
                
                # Update database with new filename
                year, month_folder = DateFormat.get_folder_path(document.document_date)
                category_path = document.category.get_full_path()
                
                new_relative_path = FilePathBuilder.build_upload_path(
                    category_path,
                    document.document_date,
                    new_filename
                )
                
                document.file.name = new_relative_path
                document.save(update_fields=['file'])
                
                return new_relative_path
        except Exception:
            # SPD info not available yet, skip rename
            pass
    
    # For Belanjaan, do nothing (already named correctly by upload_path)
    return None


def relocate_document_file(document, old_category=None, old_date=None) -> Optional[str]:
    """
    Move dan rename file ketika metadata berubah
    
    Dipanggil ketika user update category atau document_date.
    File akan dipindah ke folder yang sesuai dan di-rename.
    
    Args:
        document: Document instance dengan metadata BARU
        old_category: Previous category (optional, untuk logging)
        old_date: Previous date (optional, untuk logging)
        
    Returns:
        New relative file path jika berhasil, None jika tidak ada perubahan
        
    Examples:
        >>> # User update document_date from Jan to Feb
        >>> new_path = relocate_document_file(document)
        >>> print(new_path)
        uploads/belanjaan/atk/2024/02-Februari/ATK_2024-02-15.pdf
    
    Implementasi Standar:
        - Create target directory jika belum ada
        - Move file (not copy) untuk save space
        - Cleanup empty directories setelah move
        - Update database dengan path baru
        - Handle duplicate filenames dengan ensure_unique_filepath
        
    Catatan Pemeliharaan:
        - Dipanggil dari views saat update document
        - Error tidak boleh fail update operation
        - Log errors untuk debugging
    """
    if not document.file:
        return None
    
    try:
        old_path = document.file.path
        
        if not os.path.exists(old_path):
            return None
        
        # Generate new filename based on document type
        if document.category.slug == 'spd' or (
            document.category.parent and document.category.parent.slug == 'spd'
        ):
            try:
                new_filename = generate_spd_filename(document.spd_info)
            except Exception:
                # SPD info not available, use generic
                date_str = document.document_date.strftime(FILENAME_DATE_FORMAT)
                new_filename = f"SPD_{date_str}_{document.id}.pdf"
        else:
            new_filename = generate_document_filename(document)
        
        # Build new directory path
        category_path = document.category.get_full_path()
        new_dir = os.path.join(
            settings.MEDIA_ROOT,
            FilePathBuilder.build_directory_path(category_path, document.document_date)
        )
        
        # Create directory if not exists
        os.makedirs(new_dir, exist_ok=True)
        
        # Build new full path
        new_path = os.path.join(new_dir, new_filename)
        
        # Ensure unique filename
        new_path = ensure_unique_filepath(new_path)
        new_filename = os.path.basename(new_path)
        
        # Move file if path different
        if old_path != new_path:
            shutil.move(old_path, new_path)
            
            # Cleanup empty old directories
            try:
                old_dir = os.path.dirname(old_path)
                if not os.listdir(old_dir):
                    os.rmdir(old_dir)
                    # Try parent directory
                    parent_dir = os.path.dirname(old_dir)
                    if not os.listdir(parent_dir):
                        os.rmdir(parent_dir)
            except Exception:
                pass  # Ignore cleanup errors
            
            # Update database with new path
            new_relative_path = FilePathBuilder.build_upload_path(
                category_path,
                document.document_date,
                new_filename
            )
            
            document.file.name = new_relative_path
            document.save(update_fields=['file'])
            
            return new_relative_path
        
        return None
        
    except Exception as e:
        # Log error but don't fail the update
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error relocating file: {e}")
        return None