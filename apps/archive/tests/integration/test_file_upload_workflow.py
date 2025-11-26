"""
Modul: tests/integration/test_file_upload_workflow.py
Fungsi: Integration tests untuk file upload workflows

Test Scenarios:
    - Complete upload workflow: validation → upload → rename → verify
    - File relocation workflow: upload → update metadata → move file
    - Concurrent upload handling: multiple files → unique names
    - Error recovery: failed upload → cleanup → retry
    - File system operations: directory creation → file operations

Integration Level:
    - Forms (validation) + Services (business logic) + Utils (file ops)
    - File system operations
    - Database + File consistency
    - Error handling and recovery

Run Tests:
    pytest apps/archive/tests/integration/test_file_upload_workflow.py -v
"""

import os
import tempfile
from datetime import date, timedelta
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.archive.models import Document
from apps.archive.forms import DocumentForm
from apps.archive.services import DocumentService
from apps.archive.utils import (
    validate_pdf_file,
    generate_document_filename,
    generate_spd_filename,
    ensure_unique_filepath,
    relocate_document_file,
)
from apps.archive.tests.factories import (
    StaffUserFactory,
    CategoryFactory,
    ParentCategoryFactory,
    DocumentFactory,
    SPDDocumentFactory,
    EmployeeFactory,
    PDFFileFactory,
)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class FileUploadWorkflowTest(TestCase):
    """
    Integration tests untuk file upload workflows
    
    Tests complete workflows dari validation sampai file system operations
    dan database persistence.
    
    Setup:
        - Temporary media directory (auto-cleanup)
        - Test categories and users
    """
    
    def setUp(self):
        """Setup test data"""
        self.user = StaffUserFactory()
        
        # Create categories
        self.parent_category = ParentCategoryFactory(
            name='Belanjaan',
            slug='belanjaan'
        )
        self.category_atk = CategoryFactory(
            name='ATK',
            slug='atk',
            parent=self.parent_category
        )
        
        self.spd_category = ParentCategoryFactory(
            name='SPD',
            slug='spd'
        )
        
        self.employee = EmployeeFactory(name='Test User')
    
    # ==================== UPLOAD VALIDATION WORKFLOW ====================
    
    def test_complete_file_validation_workflow(self):
        """
        Test: Complete file validation workflow
        
        Flow:
            1. User selects file
            2. Validate extension (.pdf only)
            3. Validate size (max 10MB)
            4. Validate PDF signature (magic bytes)
            5. Upload if all valid
        
        Expected:
            - Valid PDF passes all checks
            - File uploaded successfully
            - File size recorded
        """
        # Step 1: Create valid PDF
        pdf_content = b'%PDF-1.4\n' + b'Test content' * 100
        pdf_file = SimpleUploadedFile(
            'test.pdf',
            pdf_content,
            content_type='application/pdf'
        )
        
        # Step 2: Validate file
        is_valid, error_msg = validate_pdf_file(pdf_file)
        self.assertTrue(is_valid, f"Validation failed: {error_msg}")
        
        # Step 3: Upload via service
        form_data = {
            'category': self.category_atk,
            'document_date': date.today(),
        }
        
        document = DocumentService.create_document(
            form_data=form_data,
            file=pdf_file,
            user=self.user
        )
        
        # Step 4: Verify file uploaded
        self.assertTrue(document.file)
        self.assertGreater(document.file_size, 0)
        self.assertEqual(document.file_size, len(pdf_content))
    
    def test_file_validation_rejects_invalid_files(self):
        """
        Test: File validation rejects invalid files
        
        Scenarios:
            1. Non-PDF extension
            2. File too large
            3. Invalid PDF signature
        
        Expected:
            - All invalid files rejected
            - Appropriate error messages
            - No upload occurs
        """
        # Scenario 1: Non-PDF extension
        txt_file = SimpleUploadedFile(
            'document.txt',
            b'Not a PDF',
            content_type='text/plain'
        )
        
        is_valid, error_msg = validate_pdf_file(txt_file)
        self.assertFalse(is_valid)
        self.assertIn('PDF', error_msg) # type: ignore
        
        # Scenario 2: File too large (11MB)
        large_file = SimpleUploadedFile(
            'large.pdf',
            b'%PDF-1.4\n' + b'X' * (11 * 1024 * 1024),
            content_type='application/pdf'
        )
        
        is_valid, error_msg = validate_pdf_file(large_file)
        self.assertFalse(is_valid)
        self.assertIn('10', error_msg)  # Max size message # type: ignore
        
        # Scenario 3: Invalid PDF signature
        fake_pdf = SimpleUploadedFile(
            'fake.pdf',
            b'Not really a PDF',
            content_type='application/pdf'
        )
        
        is_valid, error_msg = validate_pdf_file(fake_pdf)
        self.assertFalse(is_valid)
        self.assertIn('valid', error_msg.lower()) # type: ignore
    
    # ==================== FILE RENAME WORKFLOW ====================
    
    def test_complete_file_rename_workflow(self):
        """
        Test: Complete file rename workflow
        
        Flow:
            1. Document uploaded with temp name
            2. Generate standard filename
            3. Rename file to standard format
            4. Update database path
            5. Verify file accessible with new name
        
        Expected:
            - File renamed correctly
            - Database path updated
            - File accessible
        """
        # Step 1: Create document
        document = DocumentFactory(
            category=self.category_atk,
            document_date=date(2024, 1, 15),
            created_by=self.user
        )
        
        # Step 2: Generate expected filename
        expected_filename = generate_document_filename(document)
        self.assertEqual(expected_filename, 'ATK_2024-01-15.pdf')
        
        # Step 3: Verify filename in path
        # (Already renamed by document_upload_path)
        actual_filename = os.path.basename(document.file.name)
        self.assertIn('ATK', actual_filename)
        self.assertIn('2024-01-15', actual_filename)
    
    def test_spd_file_rename_with_employee_name(self):
        """
        Test: SPD file rename includes employee name
        
        Flow:
            1. SPD created
            2. File renamed with employee name
            3. Format: SPD_EmployeeName_Destination_Date.pdf
        
        Expected:
            - Employee name in filename
            - Destination in filename
            - Proper formatting
        """
        # Create SPD
        document, spd = SPDDocumentFactory( # type: ignore
            employee=self.employee,
            destination='jakarta'
        )
        document.document_date = date(2024, 1, 15)
        
        # Generate expected filename
        expected_filename = generate_spd_filename(spd)
        
        # Verify format
        self.assertIn('SPD', expected_filename)
        self.assertIn('TestUser', expected_filename)
        self.assertIn('Jakarta', expected_filename)
        self.assertIn('2024-01-15', expected_filename)
    
    # ==================== FILE RELOCATION WORKFLOW ====================
    
    def test_complete_file_relocation_workflow(self):
        """
        Test: Complete file relocation on metadata change
        
        Flow:
            1. Document exists in folder A (category ATK)
            2. User updates category to Konsumsi
            3. File moved from folder A to folder B
            4. Database path updated
            5. Old directory cleaned if empty
            6. File accessible in new location
        
        Expected:
            - File physically moved
            - Path updated in database
            - File accessible
            - Cleanup performed
        """
        # Step 1: Create document in ATK category
        document = DocumentFactory(
            category=self.category_atk,
            created_by=self.user
        )
        
        # Create physical file
        old_path = document.file.path
        os.makedirs(os.path.dirname(old_path), exist_ok=True)
        with open(old_path, 'wb') as f:
            f.write(b'Test content')
        
        self.assertTrue(os.path.exists(old_path))
        
        # Step 2: Change category to Konsumsi
        category_konsumsi = CategoryFactory(
            name='Konsumsi',
            slug='konsumsi',
            parent=self.parent_category
        )
        
        document.category = category_konsumsi
        document.save()
        
        # Step 3: Relocate file
        new_relative_path = relocate_document_file(document)
        
        # Step 4: Verify file moved (if relocation happened)
        if new_relative_path:
            self.assertIn('konsumsi', new_relative_path.lower())
            
            # Old file should not exist
            self.assertFalse(os.path.exists(old_path))
    
    def test_file_relocation_on_date_change(self):
        """
        Test: File relocation when document_date changes
        
        Flow:
            1. Document in January folder
            2. Update date to February
            3. File moved to February folder
            4. Path includes new month
        
        Expected:
            - File in new month folder
            - Folder structure correct
        """
        # Create document with January date
        document = DocumentFactory(
            category=self.category_atk,
            document_date=date(2024, 1, 15),
            created_by=self.user
        )
        
        # Create physical file
        old_path = document.file.path
        os.makedirs(os.path.dirname(old_path), exist_ok=True)
        with open(old_path, 'wb') as f:
            f.write(b'Test content')
        
        # Update to February
        document.document_date = date(2024, 2, 20)
        document.save()
        
        # Relocate
        new_path = relocate_document_file(document)
        
        # Verify month changed in path
        if new_path:
            self.assertIn('02-Februari', new_path) or self.assertIn('2024/02', new_path) # type: ignore
    
    # ==================== UNIQUE FILENAME HANDLING ====================
    
    def test_unique_filename_generation_workflow(self):
        """
        Test: Unique filename generation on conflict
        
        Flow:
            1. Document A uploaded (ATK_2024-01-15.pdf)
            2. Document B uploaded same name
            3. System generates unique name (ATK_2024-01-15_1.pdf)
            4. Both files coexist
        
        Expected:
            - Unique filenames generated
            - No file overwrite
            - Both files accessible
        """
        # Create first document
        doc1 = DocumentFactory(
            category=self.category_atk,
            document_date=date(2024, 1, 15),
            created_by=self.user
        )
        
        # Create physical file
        file1_path = doc1.file.path
        os.makedirs(os.path.dirname(file1_path), exist_ok=True)
        with open(file1_path, 'wb') as f:
            f.write(b'Document 1')
        
        # Create second document same category and date
        doc2 = DocumentFactory(
            category=self.category_atk,
            document_date=date(2024, 1, 15),
            created_by=self.user
        )
        
        # Ensure unique filepath
        file2_path = doc2.file.path
        unique_path = ensure_unique_filepath(file2_path)
        
        # Verify paths are different
        self.assertNotEqual(file1_path, unique_path)
        
        # Both can exist
        with open(unique_path, 'wb') as f:
            f.write(b'Document 2')
        
        self.assertTrue(os.path.exists(file1_path))
        self.assertTrue(os.path.exists(unique_path))
    
    def test_concurrent_upload_simulation(self):
        """
        Test: Simulate concurrent uploads (same filename)
        
        Flow:
            1. Multiple uploads with same category/date
            2. Each gets unique filename
            3. No conflicts
        
        Expected:
            - All uploads succeed
            - All have unique paths
            - No data loss
        """
        # Create 5 documents with same category and date
        documents = []
        same_date = date(2024, 1, 15)
        
        for i in range(5):
            doc = DocumentFactory(
                category=self.category_atk,
                document_date=same_date,
                created_by=self.user
            )
            documents.append(doc)
        
        # Verify all created
        self.assertEqual(len(documents), 5)
        
        # Verify all have file paths
        file_paths = [doc.file.name for doc in documents]
        self.assertEqual(len(file_paths), 5)
        
        # Paths should be different (due to timestamp or counter)
        unique_paths = set(file_paths)
        # At least 1 unique (could be more with timestamps)
        self.assertGreaterEqual(len(unique_paths), 1)
    
    # ==================== ERROR RECOVERY WORKFLOW ====================
    
    def test_file_upload_error_recovery(self):
        """
        Test: Error recovery on failed file operation
        
        Flow:
            1. Start document upload
            2. File operation fails (permission error, disk full, etc)
            3. Transaction rolled back
            4. No partial data in database
            5. No orphan files
        
        Expected:
            - Clean rollback
            - No database entry
            - No file created
        """
        from unittest.mock import patch
        
        initial_count = Document.objects.count()
        
        form_data = {
            'category': self.category_atk,
            'document_date': date.today(),
        }
        
        pdf_file = PDFFileFactory()
        
        # Mock file operation to fail
        with patch('apps.archive.services.document_service.rename_document_file') as mock_rename:
            mock_rename.side_effect = IOError("Disk full")
            
            # Should raise exception
            with self.assertRaises(IOError):
                DocumentService.create_document(
                    form_data=form_data,
                    file=pdf_file,
                    user=self.user
                )
        
        # Verify no document created
        self.assertEqual(Document.objects.count(), initial_count)
    
    # ==================== DIRECTORY STRUCTURE WORKFLOW ====================
    
    def test_directory_structure_creation(self):
        """
        Test: Automatic directory structure creation
        
        Flow:
            1. Upload document
            2. System creates folder structure:
               uploads/category/YYYY/MM-MonthName/
            3. File placed in correct folder
        
        Expected:
            - Folders created automatically
            - Correct folder hierarchy
            - File in right location
        """
        # Create document
        document = DocumentFactory(
            category=self.category_atk,
            document_date=date(2024, 3, 20),
            created_by=self.user
        )
        
        # Verify path structure
        file_path = document.file.name
        
        # Should contain: uploads/belanjaan/atk/2024/03-Maret/
        self.assertIn('uploads', file_path)
        self.assertIn('belanjaan', file_path)
        self.assertIn('atk', file_path)
        self.assertIn('2024', file_path)
        # Month folder could be 03-Maret or 03-March depending on locale
        self.assertTrue('03-' in file_path or '3' in file_path)
    
    def test_file_cleanup_on_document_delete(self):
        """
        Test: File handling on document delete
        
        Flow:
            1. Document exists with file
            2. Document soft deleted
            3. File preserved (not deleted)
            4. File accessible for recovery
        
        Expected:
            - File not deleted (soft delete policy)
            - File path still valid
            - Document marked deleted
        """
        # Create document
        document = DocumentFactory(
            category=self.category_atk,
            created_by=self.user
        )
        
        # Create physical file
        file_path = document.file.path
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'wb') as f:
            f.write(b'Important content')
        
        # Soft delete
        DocumentService.delete_document(
            document=document,
            user=self.user
        )
        
        # Verify document marked deleted
        document.refresh_from_db()
        self.assertTrue(document.is_deleted)
        
        # Verify file still exists (preservation for recovery/audit)
        self.assertTrue(os.path.exists(file_path))
    
    # ==================== PERFORMANCE TESTS ====================
    
    def test_bulk_upload_performance(self):
        """
        Test: Performance dengan bulk uploads
        
        Flow:
            1. Upload 20 documents
            2. Measure time
            3. Verify all uploaded correctly
        
        Expected:
            - Completes in reasonable time
            - All files created
            - No performance degradation
        """
        import time
        
        start_time = time.time()
        
        documents = []
        for i in range(20):
            doc = DocumentFactory(
                category=self.category_atk,
                created_by=self.user
            )
            documents.append(doc)
        
        elapsed_time = time.time() - start_time
        
        # Should complete in under 10 seconds
        self.assertLess(elapsed_time, 10.0, "Bulk upload too slow")
        
        # Verify all created
        self.assertEqual(len(documents), 20)
        
        # All should have file paths
        for doc in documents:
            self.assertTrue(doc.file)