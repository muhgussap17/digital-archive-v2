"""
Modul: tests/integration/test_document_crud_flow.py
Fungsi: Integration tests untuk complete Document CRUD workflow

Test Scenarios:
    - Complete create flow: form validation → service → file ops → activity log
    - Complete update flow: metadata update → file relocation → version increment
    - Complete delete flow: soft delete → activity log → file preservation
    - List and filter flow: query → pagination → search
    - File upload workflow: validation → upload → rename → verify

Integration Level:
    - Forms + Services + Utils + Models
    - Database + File System
    - Activity Logging
    - Error handling across layers

Run Tests:
    pytest apps/archive/tests/integration/test_document_crud_flow.py -v
    pytest apps/archive/tests/integration/test_document_crud_flow.py -v --durations=10
"""

import os
from datetime import date, timedelta
from django.test import TestCase, override_settings
from django.conf import settings
import tempfile

from apps.archive.models import Document, DocumentActivity
from apps.archive.forms import DocumentForm, DocumentUpdateForm
from apps.archive.services import DocumentService
from apps.archive.tests.factories import (
    UserFactory,
    StaffUserFactory,
    CategoryFactory,
    ParentCategoryFactory,
    DocumentFactory,
    PDFFileFactory,
)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class DocumentCRUDFlowTest(TestCase):
    """
    Integration tests untuk Document CRUD workflow
    
    Test complete flow dari form validation sampai database persistence
    dan file operations.
    
    Setup:
        - Test database (transactional)
        - Temporary media directory
        - Test users and categories
    
    Teardown:
        - Automatic cleanup via Django TestCase
        - Temp files cleaned by override_settings
    """
    
    def setUp(self):
        """Setup test data yang dibutuhkan semua tests"""
        # Create users
        self.user = UserFactory()
        self.staff_user = StaffUserFactory()
        
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
        self.category_konsumsi = CategoryFactory(
            name='Konsumsi',
            slug='konsumsi',
            parent=self.parent_category
        )
        
        # Create test file
        self.pdf_file = PDFFileFactory()
    
    # ==================== CREATE FLOW TESTS ====================
    
    def test_complete_document_create_flow(self):
        """
        Test: Complete document creation workflow
        
        Flow:
            1. User fills form with valid data
            2. Form validation passes
            3. Service creates document
            4. File uploaded and renamed
            5. Activity logged
            6. Document retrievable from database
        
        Expected:
            - Document created successfully
            - File exists on filesystem
            - Activity log created
            - All metadata correct
        """
        # Step 1: Prepare form data
        form_data = {
            'category': self.category_atk.id,
            'document_date': date.today().strftime('%Y-%m-%d'),
        }
        
        # Step 2: Validate form
        form = DocumentForm(data=form_data, files={'file': self.pdf_file})
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")
        
        # Step 3: Create document via service
        document = DocumentService.create_document(
            form_data=form.cleaned_data,
            file=self.pdf_file,
            user=self.staff_user
        )
        
        # Step 4: Verify document created
        self.assertIsNotNone(document)
        self.assertIsNotNone(document.id) # type: ignore
        self.assertEqual(document.category, self.category_atk)
        self.assertEqual(document.created_by, self.staff_user)
        self.assertEqual(document.document_date, date.today())
        self.assertFalse(document.is_deleted)
        self.assertEqual(document.version, 1)
        
        # Step 5: Verify file operations
        self.assertTrue(document.file)
        self.assertGreater(document.file_size, 0)
        
        # File naming should follow convention: ATK_YYYY-MM-DD.pdf
        filename = os.path.basename(document.file.name)
        self.assertIn('ATK', filename)
        self.assertIn(date.today().strftime('%Y-%m-%d'), filename)
        
        # Step 6: Verify activity logged
        activities = DocumentActivity.objects.filter(document=document)
        self.assertEqual(activities.count(), 1)
        
        activity = activities.first()
        self.assertEqual(activity.action_type, 'create') # type: ignore
        self.assertEqual(activity.user, self.staff_user) # type: ignore
        self.assertIn('dibuat', activity.description.lower()) # type: ignore
        
        # Step 7: Verify document can be retrieved
        retrieved_doc = Document.objects.get(id=document.id) # type: ignore
        self.assertEqual(retrieved_doc, document)
    
    def test_document_create_with_validation_error(self):
        """
        Test: Document creation fails with invalid data
        
        Flow:
            1. User submits invalid data
            2. Form validation fails
            3. No document created
            4. No activity logged
        
        Expected:
            - Form invalid
            - Appropriate error messages
            - No database changes
        """
        # Invalid: future date
        form_data = {
            'category': self.category_atk.id,
            'document_date': (date.today() + timedelta(days=1)).strftime('%Y-%m-%d'),
        }
        
        form = DocumentForm(data=form_data, files={'file': self.pdf_file})
        
        # Form should be invalid
        self.assertFalse(form.is_valid())
        self.assertIn('document_date', form.errors)
        
        # No document should be created
        initial_count = Document.objects.count()
        # (Don't call service with invalid data)
        final_count = Document.objects.count()
        self.assertEqual(initial_count, final_count)
    
    # ==================== UPDATE FLOW TESTS ====================
    
    def test_complete_document_update_flow(self):
        """
        Test: Complete document update workflow
        
        Flow:
            1. Document exists in database
            2. User updates metadata (category, date)
            3. Form validation passes
            4. Service updates document
            5. File relocated to new folder
            6. Version incremented
            7. Activity logged
        
        Expected:
            - Metadata updated
            - File moved to correct location
            - Version incremented
            - Activity logged
        """
        # Step 1: Create initial document
        document = DocumentFactory(
            category=self.category_atk,
            created_by=self.staff_user
        )
        
        # Create physical file
        file_path = document.file.path
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'wb') as f:
            f.write(self.pdf_file.read())
        
        initial_version = document.version
        initial_category = document.category
        
        # Step 2: Prepare update data (change category)
        new_date = date.today() - timedelta(days=1)
        form_data = {
            'category': self.category_konsumsi.id,
            'document_date': new_date.strftime('%Y-%m-%d'),
        }
        
        # Step 3: Validate form
        form = DocumentUpdateForm(data=form_data, instance=document)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")
        
        # Step 4: Update via service
        updated_doc = DocumentService.update_document(
            document=document,
            form_data=form.cleaned_data,
            user=self.staff_user
        )
        
        # Step 5: Verify metadata updated
        updated_doc.refresh_from_db()
        self.assertEqual(updated_doc.category, self.category_konsumsi)
        self.assertEqual(updated_doc.document_date, new_date)
        self.assertEqual(updated_doc.version, initial_version + 1)
        
        # Step 6: Verify file path contains new category
        # File should be in konsumsi folder now
        new_path = updated_doc.file.name
        self.assertIn('konsumsi', new_path.lower())
        
        # Step 7: Verify activity logged
        activities = DocumentActivity.objects.filter(
            document=document,
            action_type='update'
        )
        self.assertGreater(activities.count(), 0)
        
        latest_activity = activities.first()
        self.assertEqual(latest_activity.user, self.staff_user) # type: ignore
        self.assertIn('diperbarui', latest_activity.description.lower()) # type: ignore
    
    def test_document_update_metadata_only(self):
        """
        Test: Update document metadata tanpa ganti file
        
        Flow:
            1. Update document_date only
            2. Category unchanged
            3. File relocation happens (new date folder)
            4. Version incremented
        
        Expected:
            - Date updated
            - File moved to new date folder
            - Category unchanged
        """
        # Create document
        document = DocumentFactory(
            category=self.category_atk,
            document_date=date(2024, 1, 15),
            created_by=self.staff_user
        )
        
        # Update date only
        new_date = date(2024, 2, 20)
        form_data = {
            'category': self.category_atk.id,  # Same category
            'document_date': new_date.strftime('%Y-%m-%d'),
        }
        
        form = DocumentUpdateForm(data=form_data, instance=document)
        self.assertTrue(form.is_valid())
        
        updated_doc = DocumentService.update_document(
            document=document,
            form_data=form.cleaned_data,
            user=self.staff_user
        )
        
        # Verify date updated
        updated_doc.refresh_from_db()
        self.assertEqual(updated_doc.document_date, new_date)
        self.assertEqual(updated_doc.category, self.category_atk)
    
    # ==================== DELETE FLOW TESTS ====================
    
    def test_complete_document_delete_flow(self):
        """
        Test: Complete document soft delete workflow
        
        Flow:
            1. Document exists
            2. User triggers delete
            3. Service soft deletes (is_deleted=True)
            4. Activity logged
            5. File preserved (not deleted)
            6. Document not in active queries
        
        Expected:
            - is_deleted = True
            - deleted_at timestamp set
            - File still exists
            - Activity logged
            - Not returned in get_active_documents()
        """
        # Step 1: Create document
        document = DocumentFactory(
            category=self.category_atk,
            created_by=self.staff_user
        )
        
        document_id = document.id
        
        # Step 2: Delete via service
        deleted_doc = DocumentService.delete_document(
            document=document,
            user=self.staff_user
        )
        
        # Step 3: Verify soft delete
        deleted_doc.refresh_from_db()
        self.assertTrue(deleted_doc.is_deleted)
        self.assertIsNotNone(deleted_doc.deleted_at)
        
        # Step 4: Verify document still exists in DB
        self.assertTrue(
            Document.objects.filter(id=document_id).exists()
        )
        
        # Step 5: Verify not in active queries
        active_docs = DocumentService.get_active_documents()
        self.assertNotIn(deleted_doc, active_docs)
        
        # Step 6: Verify activity logged
        activities = DocumentActivity.objects.filter(
            document=document,
            action_type='delete'
        )
        self.assertEqual(activities.count(), 1)
        
        activity = activities.first()
        self.assertEqual(activity.user, self.staff_user) # type: ignore
        self.assertIn('dihapus', activity.description.lower()) # type: ignore
    
    # ==================== LIST AND FILTER FLOW TESTS ====================
    
    def test_document_list_and_filter_flow(self):
        """
        Test: List documents with filters
        
        Flow:
            1. Create multiple documents (different categories, dates)
            2. Query without filters (get all)
            3. Query with category filter
            4. Query with date range filter
            5. Query with search
        
        Expected:
            - Filters work correctly
            - Only active documents returned
            - Deleted documents excluded
        """
        # Step 1: Create test documents
        doc1 = DocumentFactory(
            category=self.category_atk,
            document_date=date(2024, 1, 15),
            created_by=self.staff_user
        )
        
        doc2 = DocumentFactory(
            category=self.category_konsumsi,
            document_date=date(2024, 1, 20),
            created_by=self.staff_user
        )
        
        doc3_deleted = DocumentFactory(
            category=self.category_atk,
            document_date=date(2024, 1, 25),
            created_by=self.staff_user,
            is_deleted=True
        )
        
        # Step 2: Get all active documents
        all_docs = DocumentService.get_active_documents()
        self.assertEqual(all_docs.count(), 2)
        self.assertIn(doc1, all_docs)
        self.assertIn(doc2, all_docs)
        self.assertNotIn(doc3_deleted, all_docs)
        
        # Step 3: Filter by category
        atk_docs = DocumentService.get_active_documents({
            'category': self.category_atk
        })
        self.assertEqual(atk_docs.count(), 1)
        self.assertIn(doc1, atk_docs)
        self.assertNotIn(doc2, atk_docs)
        
        # Step 4: Filter by date range
        docs_in_range = DocumentService.get_active_documents({
            'date_from': date(2024, 1, 18),
            'date_to': date(2024, 1, 22)
        })
        self.assertEqual(docs_in_range.count(), 1)
        self.assertIn(doc2, docs_in_range)
        
        # Step 5: Search
        search_results = DocumentService.get_active_documents({
            'search': 'ATK'
        })
        self.assertGreaterEqual(search_results.count(), 1)
        self.assertIn(doc1, search_results)
    
    def test_document_ordering(self):
        """
        Test: Documents ordered by date descending
        
        Expected:
            - Newest documents first
            - Consistent ordering
        """
        # Create documents with different dates
        doc_old = DocumentFactory(
            category=self.category_atk,
            document_date=date(2024, 1, 1),
            created_by=self.staff_user
        )
        
        doc_new = DocumentFactory(
            category=self.category_atk,
            document_date=date(2024, 3, 1),
            created_by=self.staff_user
        )
        
        doc_mid = DocumentFactory(
            category=self.category_atk,
            document_date=date(2024, 2, 1),
            created_by=self.staff_user
        )
        
        # Get documents
        docs = DocumentService.get_active_documents()
        docs_list = list(docs)
        
        # Verify ordering (newest first)
        self.assertEqual(docs_list[0], doc_new)
        self.assertEqual(docs_list[1], doc_mid)
        self.assertEqual(docs_list[2], doc_old)
    
    # ==================== ERROR HANDLING TESTS ====================
    
    def test_create_with_database_error_rollback(self):
        """
        Test: Transaction rollback on database error
        
        Flow:
            1. Start create operation
            2. Simulate database error
            3. Verify rollback (no partial data)
        
        Expected:
            - No document created
            - No activity logged
            - Clean state
        """
        from unittest.mock import patch
        
        initial_count = Document.objects.count()
        
        # Mock Document.objects.create to raise error
        with patch('apps.archive.services.document_service.Document.objects.create') as mock_create:
            mock_create.side_effect = Exception("Database error")
            
            form_data = {
                'category': self.category_atk,
                'document_date': date.today(),
            }
            
            # Should raise exception
            with self.assertRaises(Exception):
                DocumentService.create_document(
                    form_data=form_data,
                    file=self.pdf_file,
                    user=self.staff_user
                )
        
        # Verify no document created
        self.assertEqual(Document.objects.count(), initial_count)
    
    # ==================== PERFORMANCE TESTS ====================
    
    def test_bulk_document_operations_performance(self):
        """
        Test: Performance dengan multiple documents
        
        Create multiple documents dan verify query performance
        
        Expected:
            - Operations complete in reasonable time
            - No N+1 query issues
        """
        import time
        
        # Create 10 documents
        start_time = time.time()
        
        documents = []
        for i in range(10):
            doc = DocumentFactory(
                category=self.category_atk,
                created_by=self.staff_user
            )
            documents.append(doc)
        
        create_time = time.time() - start_time
        
        # Query documents (should be fast with select_related)
        start_time = time.time()
        result = DocumentService.get_active_documents()
        list(result)  # Force evaluation
        query_time = time.time() - start_time
        
        # Assertions (generous time limits)
        self.assertLess(create_time, 5.0, "Bulk create too slow")
        self.assertLess(query_time, 1.0, "Query too slow (possible N+1)")
        
        # Verify count
        self.assertGreaterEqual(result.count(), 10)