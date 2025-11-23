"""
Modul: constants.py
Fungsi: Menyimpan semua konstanta aplikasi untuk konsistensi dan maintainability

Implementasi Standar:
    - Mengikuti PEP 8 untuk naming conventions (UPPER_CASE)
    - Centralized configuration untuk mudah maintenance
    - Type hints untuk better IDE support

Catatan Pemeliharaan:
    - Semua magic numbers dan strings harus didefinisikan di sini
    - Jangan hardcode values di code, import dari file ini
    - Update constants ini jika ada perubahan requirement
"""

from typing import List, Tuple

# ==================== FILE UPLOAD SETTINGS ====================

# Maximum file size (bytes)
MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
MAX_FILE_SIZE_MB: int = 10  # For display purposes

# Allowed file extensions
ALLOWED_FILE_EXTENSIONS: List[str] = ['pdf']

# PDF file signature (magic bytes)
PDF_FILE_SIGNATURE: bytes = b'%PDF'

# ==================== FILE NAMING CONVENTIONS ====================

# SPD filename format: SPD_NamaPegawai_Tujuan_YYYY-MM-DD.pdf
SPD_FILENAME_FORMAT: str = "SPD_{employee}_{destination}_{date}.pdf"

# Document filename format: Kategori_YYYY-MM-DD.pdf
DOCUMENT_FILENAME_FORMAT: str = "{category}_{date}.pdf"

# Date format for filenames
FILENAME_DATE_FORMAT: str = "%Y-%m-%d"

# ==================== UPLOAD PATH STRUCTURE ====================

# Base upload directory
UPLOAD_BASE_DIR: str = "uploads"

# Path format: uploads/category/YYYY/MM-MonthName/
UPLOAD_PATH_FORMAT: str = "{base}/{category}/{year}/{month}/{filename}"

# Month format for folder names (e.g., "01-Januari")
MONTH_FOLDER_FORMAT: str = "%m-%B"

# ==================== FILE SIZE FORMATTING ====================

# Units for file size display
FILE_SIZE_UNITS: List[str] = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

# Conversion factor (1024 bytes = 1 KB)
FILE_SIZE_CONVERSION_FACTOR: int = 1024

# ==================== DATE FORMATTING ====================

# Indonesian month names (for display)
INDONESIAN_MONTHS: dict = {
    1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April',
    5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus',
    9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
}

# Indonesian month names (short version)
INDONESIAN_MONTHS_SHORT: dict = {
    1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr',
    5: 'Mei', 6: 'Jun', 7: 'Jul', 8: 'Agu',
    9: 'Sep', 10: 'Okt', 11: 'Nov', 12: 'Des'
}

# Indonesian day names
INDONESIAN_DAYS: dict = {
    0: 'Senin', 1: 'Selasa', 2: 'Rabu', 3: 'Kamis',
    4: 'Jumat', 5: 'Sabtu', 6: 'Minggu'
}

# ==================== ACTIVITY LOGGING ====================

# Activity types (must match model choices)
ACTIVITY_TYPE_CREATE: str = 'create'
ACTIVITY_TYPE_VIEW: str = 'view'
ACTIVITY_TYPE_DOWNLOAD: str = 'download'
ACTIVITY_TYPE_UPDATE: str = 'update'
ACTIVITY_TYPE_DELETE: str = 'delete'

# Activity type choices (for validation)
ACTIVITY_TYPES: List[str] = [
    ACTIVITY_TYPE_CREATE,
    ACTIVITY_TYPE_VIEW,
    ACTIVITY_TYPE_DOWNLOAD,
    ACTIVITY_TYPE_UPDATE,
    ACTIVITY_TYPE_DELETE,
]

# ==================== REGEX PATTERNS ====================

# Pattern untuk membersihkan filename (keep alphanumeric, spaces, hyphens)
FILENAME_CLEAN_PATTERN: str = r'[^\w\s-]'

# Pattern untuk menghapus multiple spaces/hyphens
FILENAME_SPACES_PATTERN: str = r'[-\s]+'

# ==================== ERROR MESSAGES ====================

# File validation errors
ERROR_INVALID_EXTENSION: str = "File harus berformat PDF"
ERROR_FILE_TOO_LARGE: str = "Ukuran file maksimal {max_size} MB"
ERROR_INVALID_PDF: str = "File bukan PDF yang valid"
ERROR_FILE_NOT_FOUND: str = "File tidak ditemukan"

# Document operation errors
ERROR_DOCUMENT_NOT_FOUND: str = "Dokumen tidak ditemukan"
ERROR_PERMISSION_DENIED: str = "Anda tidak memiliki akses untuk operasi ini"
ERROR_UPLOAD_FAILED: str = "Gagal mengupload dokumen: {reason}"
ERROR_DELETE_FAILED: str = "Gagal menghapus dokumen: {reason}"

# ==================== SUCCESS MESSAGES ====================

SUCCESS_DOCUMENT_UPLOADED: str = "Dokumen berhasil diupload"
SUCCESS_DOCUMENT_UPDATED: str = "Dokumen berhasil diperbarui"
SUCCESS_DOCUMENT_DELETED: str = "Dokumen berhasil dihapus"

# ==================== CATEGORY SLUGS ====================

# Primary category slugs (must match database)
CATEGORY_SPD: str = 'spd'
CATEGORY_BELANJAAN: str = 'belanjaan'

# ==================== HTTP HEADERS ====================

# AJAX request header
AJAX_HEADER_NAME: str = 'HTTP_X_REQUESTED_WITH'
AJAX_HEADER_VALUE: str = 'XMLHttpRequest'

# Client info headers
CLIENT_IP_HEADER: str = 'HTTP_X_FORWARDED_FOR'
CLIENT_IP_FALLBACK: str = 'REMOTE_ADDR'
USER_AGENT_HEADER: str = 'HTTP_USER_AGENT'

# ==================== PAGINATION ====================

# Default items per page
PAGINATION_DEFAULT_PAGE_SIZE: int = 10
PAGINATION_DOCUMENT_LIST_PAGE_SIZE: int = 5

# ==================== BACKUP SETTINGS ====================

# Backup retention period (days)
BACKUP_RETENTION_DAYS: int = 30

# Backup file format
BACKUP_DATE_FORMAT: str = "%Y%m%d_%H%M%S"

# ==================== VALIDATION RULES ====================

# NIP validation
NIP_LENGTH: int = 18  # Standard PNS NIP length

# Document date validation
DOCUMENT_DATE_MAX_FUTURE_DAYS: int = 0  # Cannot be in the future

# ==================== DESTINATION CHOICES ====================

# SPD destination choices (must match model)
DESTINATION_CHOICES: List[Tuple[str, str]] = [
    # Dalam Provinsi Kalimantan Timur
    ('balikpapan', 'Balikpapan'),
    ('samarinda', 'Samarinda'),
    ('bontang', 'Bontang'),
    ('kutai_kartanegara', 'Kutai Kartanegara'),
    ('paser', 'Paser'),
    ('berau', 'Berau'),
    ('kutai_barat', 'Kutai Barat'),
    ('kutai_timur', 'Kutai Timur'),
    ('penajam_paser_utara', 'Penajam Paser Utara'),
    ('mahakam_ulu', 'Mahakam Ulu'),
    
    # Luar Provinsi (Frequent destinations)
    ('jakarta', 'Jakarta'),
    ('surabaya', 'Surabaya'),
    ('makassar', 'Makassar'),
    ('banjarmasin', 'Banjarmasin'),
    ('yogyakarta', 'Yogyakarta'),
    ('bandung', 'Bandung'),
    ('semarang', 'Semarang'),
    ('denpasar', 'Denpasar'),
    
    # Other
    ('other', 'Lainnya'),
]

DESTINATION_OTHER_KEY: str = 'other'

# ==================== DATE & TIME HELPER CLASSES ====================

class IndonesianMonth:
    """
    Mapping bulan dalam Bahasa Indonesia
    
    Digunakan untuk konsistensi penamaan folder dan display
    sesuai dengan standar pemerintah Indonesia
    """
    
    MONTHS = {
        1: 'Januari',
        2: 'Februari',
        3: 'Maret',
        4: 'April',
        5: 'Mei',
        6: 'Juni',
        7: 'Juli',
        8: 'Agustus',
        9: 'September',
        10: 'Oktober',
        11: 'November',
        12: 'Desember'
    }
    
    MONTHS_SHORT = {
        1: 'Jan',
        2: 'Feb',
        3: 'Mar',
        4: 'Apr',
        5: 'Mei',
        6: 'Jun',
        7: 'Jul',
        8: 'Agu',
        9: 'Sep',
        10: 'Okt',
        11: 'Nov',
        12: 'Des'
    }
    
    @classmethod
    def get_month_name(cls, month_number: int) -> str:
        """
        Dapatkan nama bulan dalam Bahasa Indonesia
        
        Args:
            month_number: Nomor bulan (1-12)
            
        Returns:
            Nama bulan (e.g., "Januari")
            
        Raises:
            ValueError: Jika month_number tidak valid
        """
        if month_number not in range(1, 13):
            raise ValueError(f"Invalid month number: {month_number}")
        return cls.MONTHS[month_number]
    
    @classmethod
    def get_month_folder(cls, month_number: int) -> str:
        """
        Format folder bulan dengan prefix angka
        
        Args:
            month_number: Nomor bulan (1-12)
            
        Returns:
            Format folder (e.g., "01-Januari")
            
        Examples:
            >>> IndonesianMonth.get_month_folder(1)
            '01-Januari'
            >>> IndonesianMonth.get_month_folder(12)
            '12-Desember'
        """
        month_name = cls.get_month_name(month_number)
        return f"{month_number:02d}-{month_name}"


class DateFormat:
    """
    Format tanggal standar untuk sistem
    
    Mengikuti standar pemerintah Indonesia dan best practice Django
    """
    
    # Display formats (untuk template)
    DISPLAY_LONG = 'd F Y'  # 15 Januari 2024 (menggunakan Indonesian locale)
    DISPLAY_SHORT = 'd/m/Y'  # 15/01/2024
    DISPLAY_MEDIUM = 'd M Y'  # 15 Jan 2024
    
    # File naming formats
    FILE_NAME = '%Y-%m-%d'  # 2024-01-15
    
    # Folder naming formats
    FOLDER_YEAR = '%Y'  # 2024
    # FOLDER_MONTH tidak pakai strftime, gunakan IndonesianMonth.get_month_folder()
    
    @staticmethod
    def get_folder_path(date_obj) -> tuple:
        """
        Generate path folder dari date object
        
        Args:
            date_obj: Tanggal dokumen (datetime.date atau datetime.datetime)
            
        Returns:
            Tuple (year, month_folder)
            
        Examples:
            >>> from datetime import date
            >>> d = date(2024, 1, 15)
            >>> DateFormat.get_folder_path(d)
            ('2024', '01-Januari')
        """
        year = date_obj.strftime(DateFormat.FOLDER_YEAR)
        month_folder = IndonesianMonth.get_month_folder(date_obj.month)
        return year, month_folder


class FilePathBuilder:
    """
    Helper untuk membangun file paths dengan konsisten
    
    Menyediakan utility functions untuk generate upload paths
    yang mengikuti struktur folder standar aplikasi.
    
    Implementasi Standar:
        - Mengikuti struktur: uploads/{category}/{year}/{month}/{filename}
        - Menggunakan nama bulan dalam Bahasa Indonesia
        - Konsisten dengan document_upload_path() di models.py
    """
    
    @staticmethod
    def build_upload_path(category_path: str, date_obj, filename: str) -> str:
        """
        Build full upload path untuk document
        
        Args:
            category_path: Full category path (e.g., "belanjaan/atk")
            date_obj: Tanggal dokumen
            filename: Nama file dengan extension
            
        Returns:
            Full relative path (e.g., "uploads/belanjaan/atk/2024/01-Januari/ATK_2024-01-15.pdf")
            
        Examples:
            >>> from datetime import date
            >>> path = FilePathBuilder.build_upload_path(
            ...     "belanjaan/atk", 
            ...     date(2024, 1, 15), 
            ...     "ATK_2024-01-15.pdf"
            ... )
            >>> print(path)
            uploads/belanjaan/atk/2024/01-Januari/ATK_2024-01-15.pdf
        """
        year, month_folder = DateFormat.get_folder_path(date_obj)
        return f"{UPLOAD_BASE_DIR}/{category_path}/{year}/{month_folder}/{filename}"
    
    @staticmethod
    def build_directory_path(category_path: str, date_obj) -> str:
        """
        Build directory path (tanpa filename)
        
        Args:
            category_path: Full category path
            date_obj: Tanggal dokumen
            
        Returns:
            Directory path (e.g., "uploads/belanjaan/atk/2024/01-Januari")
            
        Examples:
            >>> from datetime import date
            >>> path = FilePathBuilder.build_directory_path("spd", date(2024, 1, 15))
            >>> print(path)
            uploads/spd/2024/01-Januari
        """
        year, month_folder = DateFormat.get_folder_path(date_obj)
        return f"{UPLOAD_BASE_DIR}/{category_path}/{year}/{month_folder}"