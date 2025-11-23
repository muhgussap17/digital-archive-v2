"""
Modul: utils/__init__.py
Fungsi: Public API untuk utility functions dengan backward compatibility

Implementasi Standar:
    - Explicit exports untuk kontrol API
    - Temporary aliases untuk smooth migration
    - Clear deprecation warnings
"""

# ==================== PUBLIC API (NEW NAMES) ====================

# File Operations
from .file_operations import (
    validate_pdf_file,
    generate_spd_filename,
    generate_document_filename,  # NEW (was: generate_belanjaan_filename)
    ensure_unique_filepath,      # NEW (was: get_unique_filepath)
    rename_document_file,
    relocate_document_file,      # NEW (was: move_document_file)
)

# Formatters
from .formatters import (
    format_file_size,
)

# Activity Logger
from .activity_logger import (
    log_document_activity,       # NEW (was: log_activity)
    extract_client_ip,           # NEW (was: get_client_ip)
    extract_user_agent,          # NEW (was: get_user_agent)
)

# ==================== __all__ DECLARATION ====================

__all__ = [
    # File Operations (NEW API)
    'validate_pdf_file',
    'generate_spd_filename',
    'generate_document_filename',
    'ensure_unique_filepath',
    'rename_document_file',
    'relocate_document_file',
    
    # Formatters
    'format_file_size',
    
    # Activity Logger (NEW API)
    'log_document_activity',
    'extract_client_ip',
    'extract_user_agent',
]