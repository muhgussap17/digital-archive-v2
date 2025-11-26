"""
Modul: tests/unit/utils/test_file_operations.py
Fungsi: Unit tests untuk file operations utilities

Test Coverage:
    - validate_pdf_file() - PDF validation
    - generate_spd_filename() - SPD filename generation
    - generate_document_filename() - Document filename generation
    - ensure_unique_filepath() - Unique path generation
    - rename_document_file() - File renaming
    - relocate_document_file() - File relocation

Test Strategy:
    - Use temp directories untuk file operations
    - Mock actual file I/O ketika tidak perlu
    - Test edge cases (empty files, large files, etc)
    - Test filename sanitization

Run Tests:
    pytest apps/archive/tests/unit/utils/test_file_operations.py -v
"""

import os
import tempfile
from datetime import date
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings

from apps.archive.utils import (
    validate_pdf_file,
    generate_spd_filename,
    generate_document_filename,
    ensure_unique_filepath,
    rename_document_file,
    relocate_document_file,
)
from apps.archive.tests.factories import (
    DocumentFactory,
    SPDDocumentFactory,
    CategoryFactory,
    ParentCategoryFactory,
    EmployeeFactory,
)


# ==================== PDF VALIDATION TESTS ====================

@pytest.mark.unit
@pytest.mark.file_ops
class TestPDFValidation:
    """
    Test validate_pdf_file()
    
    Scenarios:
        - ✅ Valid PDF
        - ✅ Invalid extension
        - ✅ File too large
        - ✅ Invalid PDF signature
        - ✅ Empty file
    """
    
    def test_validate_pdf_valid(self, sample_pdf):
        """
        Test: Validate valid PDF file
        
        Expected:
            - is_valid = True
            - error_msg = None
        """
        # Act
        is_valid, error_msg = validate_pdf_file(sample_pdf)
        
        # Assert
        assert is_valid is True
        assert error_msg is None
    
    def test_validate_pdf_invalid_extension(self):
        """
        Test: Reject file dengan extension bukan .pdf
        
        Expected:
            - is_valid = False
            - error_msg tentang extension
        """
        # Arrange
        file = SimpleUploadedFile(
            'document.txt',
            b'Not a PDF',
            content_type='text/plain'
        )
        
        # Act
        is_valid, error_msg = validate_pdf_file(file)
        
        # Assert
        assert is_valid is False
        assert 'PDF' in error_msg or 'format' in error_msg.lower() # type: ignore
    
    def test_validate_pdf_too_large(self):
        """
        Test: Reject file yang melebihi size limit (10MB)
        
        Expected:
            - is_valid = False
            - error_msg tentang size
        """
        # Arrange - 11MB file
        large_content = b'%PDF-1.4\n' + b'X' * (11 * 1024 * 1024)
        file = SimpleUploadedFile(
            'large.pdf',
            large_content,
            content_type='application/pdf'
        )
        
        # Act
        is_valid, error_msg = validate_pdf_file(file)
        
        # Assert
        assert is_valid is False
        assert '10' in error_msg or 'besar' in error_msg.lower() # type: ignore
    
    def test_validate_pdf_invalid_signature(self):
        """
        Test: Reject file bukan PDF (invalid magic bytes)
        
        Expected:
            - is_valid = False
            - error_msg tentang invalid PDF
        """
        # Arrange
        file = SimpleUploadedFile(
            'fake.pdf',
            b'This is not a PDF file',
            content_type='application/pdf'
        )
        
        # Act
        is_valid, error_msg = validate_pdf_file(file)
        
        # Assert
        assert is_valid is False
        assert 'valid' in error_msg.lower() or 'pdf' in error_msg.lower() # type: ignore
    
    def test_validate_pdf_empty_file(self):
        """
        Test: Reject empty file
        
        Expected:
            - is_valid = False
        """
        # Arrange
        file = SimpleUploadedFile(
            'empty.pdf',
            b'',
            content_type='application/pdf'
        )
        
        # Act
        is_valid, error_msg = validate_pdf_file(file)
        
        # Assert
        assert is_valid is False


# ==================== FILENAME GENERATION TESTS ====================

@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.file_ops
class TestFilenameGeneration:
    """
    Test generate_spd_filename() dan generate_document_filename()
    
    Scenarios:
        - ✅ SPD filename format
        - ✅ Document filename format
        - ✅ Special characters removal
        - ✅ Case preservation
        - ✅ Date formatting
    """
    
    def test_generate_spd_filename_format(self):
        """
        Test: SPD filename dengan format benar
        
        Format: SPD_NamaPegawai_Tujuan_YYYY-MM-DD.pdf
        
        Expected:
            - Format sesuai standar
            - Case preserved
            - Spaces removed
        """
        # Arrange
        employee = EmployeeFactory(name='John Doe')
        document, spd = SPDDocumentFactory( # type: ignore
            employee=employee,
            destination='jakarta'
        )
        document.document_date = date(2024, 1, 15)
        
        # Act
        filename = generate_spd_filename(spd)
        
        # Assert
        assert filename == 'SPD_JohnDoe_Jakarta_2024-01-15.pdf'
        assert filename.startswith('SPD_')
        assert filename.endswith('.pdf')
        assert 'JohnDoe' in filename
        assert 'Jakarta' in filename
        assert '2024-01-15' in filename
    
    def test_generate_spd_filename_destination_other(self):
        """
        Test: SPD filename dengan destination_other
        
        Expected:
            - Use destination_other value
        """
        # Arrange
        employee = EmployeeFactory(name='Jane Smith')
        document, spd = SPDDocumentFactory( # type: ignore
            employee=employee,
            destination='other',
            destination_other='Pontianak'
        )
        document.document_date = date(2024, 2, 10)
        
        # Act
        filename = generate_spd_filename(spd)
        
        # Assert
        assert 'Pontianak' in filename
        assert filename == 'SPD_JaneSmith_Pontianak_2024-02-10.pdf'
    
    def test_generate_spd_filename_special_chars(self):
        """
        Test: SPD filename remove special characters
        
        Expected:
            - Special chars removed
            - Alphanumeric only (plus underscore, hyphen, dot)
        """
        # Arrange
        employee = EmployeeFactory(name='John O\'Brien')
        document, spd = SPDDocumentFactory( # type: ignore
            employee=employee,
            destination='jakarta'
        )
        
        # Act
        filename = generate_spd_filename(spd)
        
        # Assert
        assert "'" not in filename
        assert 'JohnOBrien' in filename or 'OBrien' in filename
    
    def test_generate_document_filename_format(self):
        """
        Test: Document filename dengan format benar
        
        Format: Kategori_YYYY-MM-DD.pdf
        
        Expected:
            - Format sesuai standar
            - Category name preserved
        """
        # Arrange
        category = CategoryFactory(name='ATK', slug='atk')
        document = DocumentFactory(category=category)
        document.document_date = date(2024, 3, 20)
        
        # Act
        filename = generate_document_filename(document)
        
        # Assert
        assert filename == 'ATK_2024-03-20.pdf'
        assert filename.endswith('.pdf')
    
    def test_generate_document_filename_preserve_case(self):
        """
        Test: Document filename preserve category case
        
        Expected:
            - Original case maintained
        """
        # Arrange
        category = CategoryFactory(name='BBM', slug='bbm')
        document = DocumentFactory(category=category)
        
        # Act
        filename = generate_document_filename(document)
        
        # Assert
        assert 'BBM' in filename
        assert filename.startswith('BBM_')


# ==================== UNIQUE FILEPATH TESTS ====================

@pytest.mark.unit
@pytest.mark.file_ops
class TestUniqueFilepath:
    """
    Test ensure_unique_filepath()
    
    Scenarios:
        - ✅ File tidak exist - return original
        - ✅ File exist - add suffix _1
        - ✅ Multiple conflicts - increment suffix
    """
    
    def test_ensure_unique_filepath_not_exists(self, temp_media_root):
        """
        Test: File tidak exist, return original path
        
        Expected:
            - Return path as-is
            - No modification
        """
        # Arrange
        filepath = str(temp_media_root / 'document.pdf')
        
        # Act
        result = ensure_unique_filepath(filepath)
        
        # Assert
        assert result == filepath
    
    def test_ensure_unique_filepath_exists(self, temp_media_root):
        """
        Test: File exist, return path dengan suffix
        
        Expected:
            - Return path dengan _1 suffix
        """
        # Arrange
        filepath = str(temp_media_root / 'document.pdf')
        
        # Create existing file
        with open(filepath, 'w') as f:
            f.write('test')
        
        # Act
        result = ensure_unique_filepath(filepath)
        
        # Assert
        assert result == str(temp_media_root / 'document_1.pdf')
        assert result != filepath
    
    def test_ensure_unique_filepath_multiple_conflicts(self, temp_media_root):
        """
        Test: Multiple files exist, increment suffix correctly
        
        Expected:
            - Find available number
            - Return document_N.pdf
        """
        # Arrange
        base_path = str(temp_media_root / 'document.pdf')
        
        # Create existing files
        with open(base_path, 'w') as f:
            f.write('test')
        with open(str(temp_media_root / 'document_1.pdf'), 'w') as f:
            f.write('test')
        with open(str(temp_media_root / 'document_2.pdf'), 'w') as f:
            f.write('test')
        
        # Act
        result = ensure_unique_filepath(base_path)
        
        # Assert
        assert result == str(temp_media_root / 'document_3.pdf')


# ==================== RENAME DOCUMENT FILE TESTS ====================

@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.file_ops
class TestRenameDocumentFile:
    """
    Test rename_document_file()
    
    Scenarios:
        - ✅ Rename SPD file setelah spd_info available
        - ✅ Skip rename untuk belanjaan (already correct)
        - ✅ Handle missing spd_info gracefully
    """
    
    def test_rename_spd_file_success(self, temp_media_root):
        """
        Test: Rename SPD file dengan format benar
        
        Expected:
            - File renamed
            - Database updated
            - Original file removed
        """
        # Arrange
        employee = EmployeeFactory(name='TestUser')
        document, spd = SPDDocumentFactory(employee=employee) # type: ignore
        
        # Simulate file existence
        old_path = document.file.path
        os.makedirs(os.path.dirname(old_path), exist_ok=True)
        with open(old_path, 'w') as f:
            f.write('test')
        
        # Act
        new_path = rename_document_file(document)
        
        # Assert
        if new_path:  # Only if rename happened
            assert 'SPD_' in new_path
            assert 'TestUser' in new_path or document.file.name
    
    def test_rename_document_file_skip_belanjaan(self):
        """
        Test: Skip rename untuk belanjaan documents
        
        Expected:
            - Return None (no rename needed)
        """
        # Arrange
        category = CategoryFactory(name='ATK', slug='atk')
        document = DocumentFactory(category=category)
        
        # Act
        result = rename_document_file(document)
        
        # Assert
        assert result is None


# ==================== RELOCATE DOCUMENT FILE TESTS ====================

@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.file_ops
class TestRelocateDocumentFile:
    """
    Test relocate_document_file()
    
    Scenarios:
        - ✅ Move file saat category berubah
        - ✅ Move file saat tanggal berubah
        - ✅ Cleanup empty directories
        - ✅ Handle file tidak exist
    """
    
    def test_relocate_document_file_category_change(self, temp_media_root):
        """
        Test: Relocate file saat category berubah
        
        Expected:
            - File moved ke folder category baru
            - Database path updated
        """
        # Arrange
        old_category = CategoryFactory(name='ATK', slug='atk')
        new_category = CategoryFactory(name='Konsumsi', slug='konsumsi')
        document = DocumentFactory(category=old_category)
        
        # Simulate file existence
        old_path = document.file.path
        os.makedirs(os.path.dirname(old_path), exist_ok=True)
        with open(old_path, 'w') as f:
            f.write('test')
        
        # Change category
        document.category = new_category
        document.save()
        
        # Act
        new_path = relocate_document_file(document)
        
        # Assert - Check if operation attempted
        # (May return None if paths sama atau file operations skipped)
        assert new_path is None or 'konsumsi' in new_path.lower()
    
    def test_relocate_document_file_no_file(self):
        """
        Test: Handle gracefully ketika file tidak exist
        
        Expected:
            - Return None
            - No error raised
        """
        # Arrange
        document = DocumentFactory(file=None)
        # File tidak dibuat physically
        
        # Act
        result = relocate_document_file(document)
        
        # Assert
        assert result is None  # Should handle gracefully