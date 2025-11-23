"""
Modul: utils/formatters.py
Fungsi: Data formatting utilities untuk display

Berisi fungsi-fungsi untuk:
    - Format file size ke human-readable format
    - Format tanggal (future expansion)
    - Format text/string (future expansion)

Implementasi Standar:
    - Mengikuti PEP 8 naming conventions
    - Type hints untuk semua fungsi
    - Menggunakan constants dari constants.py
    - Pure functions (no side effects)

Catatan Pemeliharaan:
    - Semua formatting logic harus di module ini
    - Jangan hardcode units atau format strings
    - Keep functions pure dan easily testable
    
Dependencies:
    - apps.archive.constants: Formatting constants
"""

from typing import Union

from ..constants import (
    FILE_SIZE_UNITS,
    FILE_SIZE_CONVERSION_FACTOR,
)


def format_file_size(size_bytes: Union[int, float]) -> str:
    """
    Format file size ke human-readable format
    
    Convert bytes ke unit yang sesuai (B, KB, MB, GB, TB, PB)
    dengan automatic unit selection.
    
    Args:
        size_bytes: File size dalam bytes (int atau float)
        
    Returns:
        Formatted string dengan unit (e.g., "1.50 MB")
        
    Examples:
        >>> format_file_size(1024)
        '1.00 KB'
        >>> format_file_size(1536)
        '1.50 KB'
        >>> format_file_size(1048576)
        '1.00 MB'
        >>> format_file_size(0)
        '0.00 B'
    
    Implementasi Standar:
        - Menggunakan base 1024 (binary) untuk file size
        - 2 decimal places untuk precision
        - Support sampai Petabyte
        
    Catatan Pemeliharaan:
        - Jika perlu ubah precision, update format string
        - Jika perlu tambah unit (EB, ZB), update FILE_SIZE_UNITS
        - Keep consistent dengan Django's filesizeformat filter
    """
    size = float(size_bytes)
    
    for unit in FILE_SIZE_UNITS:
        if size < FILE_SIZE_CONVERSION_FACTOR:
            return f"{size:.2f} {unit}"
        size /= FILE_SIZE_CONVERSION_FACTOR
    
    # Fallback untuk size sangat besar
    return f"{size:.2f} {FILE_SIZE_UNITS[-1]}"