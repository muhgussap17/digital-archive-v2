"""
Modul: tests/unit/services/test_document_service.py
Fungsi: Unit tests untuk DocumentService

Test Coverage:
    - create_document() - Create document dengan file
    - update_document() - Update metadata
    - delete_document() - Soft delete
    - get_active_documents() - Query helper

Test Strategy:
    - Mock file operations untuk speed
    - Test transaction rollback scenarios
    - Test activity logging
    - Test error handling

Run Tests:
    pytest apps/archive/tests/unit/services/test_document_service.py -v
    pytest apps/archive/tests/unit/services/test_document_service.py::TestDocumentServiceCreate -v
"""

from datetime import date, timedelta
from unittest.mock import patch, Mock

import pytest
from django.db import transaction
from django.utils import timezone

from apps.archive.models import Document, DocumentActivity
from apps.archive.services import DocumentService
from apps.archive.tests.factories import (
    UserFactory,
    CategoryFactory,
    DocumentFactory,
    ParentCategoryFactory,
    PDFFileFactory,
)


# ==================== CREATE DOCUMENT TESTS ====================

@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.service
class TestDocumentServiceCreate:
    """
    Test DocumentService.create_document()
    
    Scenarios:
        - ✅ Create dengan valid data
        - ✅ Transaction rollback on error
        - ✅ File rename dipanggil
        - ✅ Activity log created
        - ✅ Error handling
    """
    
    def test_create_document_success(self):
        """
        Test: Create document berhasil dengan data valid
        
        Expected:
            - Document created di database
            - created_by assigned correctly
            - File size calculated
            - Return Document instance
        """
        # Arrange
        user = UserFactory()
        category = CategoryFactory(name='ATK', slug='atk')
        pdf_file = PDFFileFactory()
        
        form_data = {
            'category': category,
            'document_date': date.today()
        }
        
        # Act
        with patch('apps.archive.services.document_service.rename_document_file') as mock_rename:
            document = DocumentService.create_document(
                form_data=form_data,
                file=pdf_file,
                user=user
            )
        
        # Assert
        assert document is not None
        assert document.category == category
        assert document.created_by == user
        assert document.document_date == date.today()
        assert document.file_size > 0
        assert document.version == 1
        assert not document.is_deleted
        
        # Verify rename dipanggil
        mock_rename.assert_called_once_with(document)
    
    def test_create_document_with_activity_logging(self):
        """
        Test: Activity log created saat create document
        
        Expected:
            - DocumentActivity record created
            - action_type = 'create'
            - User assigned correctly
        """
        # Arrange
        user = UserFactory()
        category = CategoryFactory()
        pdf_file = PDFFileFactory()
        
        form_data = {
            'category': category,
            'document_date': date.today()
        }
        
        initial_activity_count = DocumentActivity.objects.count()
        
        # Act
        with patch('apps.archive.services.document_service.rename_document_file'):
            document = DocumentService.create_document(
                form_data=form_data,
                file=pdf_file,
                user=user
            )
        
        # Assert
        assert DocumentActivity.objects.count() == initial_activity_count + 1
        
        activity = DocumentActivity.objects.latest('created_at')
        assert activity.document == document
        assert activity.user == user
        assert activity.action_type == 'create'
        assert 'dibuat' in activity.description.lower() # type: ignore
    
    def test_create_document_transaction_rollback(self):
        """
        Test: Transaction rollback jika rename file error
        
        Expected:
            - No document created di database
            - Transaction rolled back
        """
        # Arrange
        user = UserFactory()
        category = CategoryFactory()
        pdf_file = PDFFileFactory()
        
        form_data = {
            'category': category,
            'document_date': date.today()
        }
        
        initial_count = Document.objects.count()
        
        # Act - Mock rename_document_file untuk raise exception
        with patch('apps.archive.services.document_service.rename_document_file') as mock_rename:
            mock_rename.side_effect = Exception("File operation failed")
            
            with pytest.raises(Exception):
                DocumentService.create_document(
                    form_data=form_data,
                    file=pdf_file,
                    user=user
                )
        
        # Assert - No document should be created
        assert Document.objects.count() == initial_count
    
    def test_create_document_with_request_info(self, request_factory):
        """
        Test: Activity log include IP dan User Agent dari request
        
        Expected:
            - Activity log has ip_address
            - Activity log has user_agent
        """
        # Arrange
        user = UserFactory()
        category = CategoryFactory()
        pdf_file = PDFFileFactory()
        
        form_data = {
            'category': category,
            'document_date': date.today()
        }
        
        # Create mock request
        request = request_factory.get('/')
        request.user = user
        request.META['REMOTE_ADDR'] = '192.168.1.100'
        request.META['HTTP_USER_AGENT'] = 'Test Browser'
        
        # Act
        with patch('apps.archive.services.document_service.rename_document_file'):
            document = DocumentService.create_document(
                form_data=form_data,
                file=pdf_file,
                user=user,
                request=request
            )
        
        # Assert
        activity = DocumentActivity.objects.filter(document=document).first()
        assert activity.ip_address == '192.168.1.100' # type: ignore
        assert activity.user_agent == 'Test Browser' # type: ignore


# ==================== UPDATE DOCUMENT TESTS ====================

@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.service
class TestDocumentServiceUpdate:
    """
    Test DocumentService.update_document()
    
    Scenarios:
        - ✅ Update metadata berhasil
        - ✅ Version increment
        - ✅ File relocate dipanggil
        - ✅ Activity log created
    """
    
    def test_update_document_success(self):
        """
        Test: Update document metadata berhasil
        
        Expected:
            - Category updated
            - document_date updated
            - Version incremented
            - Activity logged
        """
        # Arrange
        document = DocumentFactory()
        user = UserFactory()
        new_category = CategoryFactory(name='Konsumsi', slug='konsumsi')
        new_date = date.today() - timedelta(days=1)
        
        original_version = document.version
        
        form_data = {
            'category': new_category,
            'document_date': new_date
        }
        
        # Act
        with patch('apps.archive.services.document_service.relocate_document_file') as mock_relocate:
            updated_doc = DocumentService.update_document(
                document=document,
                form_data=form_data,
                user=user
            )
        
        # Assert
        updated_doc.refresh_from_db()
        assert updated_doc.category == new_category
        assert updated_doc.document_date == new_date
        assert updated_doc.version == original_version + 1
        
        # Verify relocate dipanggil
        mock_relocate.assert_called_once_with(updated_doc)
    
    def test_update_document_activity_logged(self):
        """
        Test: Activity log created saat update
        
        Expected:
            - DocumentActivity record created
            - action_type = 'update'
        """
        # Arrange
        document = DocumentFactory()
        user = UserFactory()
        new_category = CategoryFactory()
        
        form_data = {
            'category': new_category,
            'document_date': date.today()
        }
        
        initial_count = DocumentActivity.objects.count()
        
        # Act
        with patch('apps.archive.services.document_service.relocate_document_file'):
            DocumentService.update_document(
                document=document,
                form_data=form_data,
                user=user
            )
        
        # Assert
        assert DocumentActivity.objects.count() == initial_count + 1
        
        activity = DocumentActivity.objects.latest('created_at')
        assert activity.action_type == 'update'
        assert activity.document == document
        assert activity.user == user
    
    def test_update_document_transaction_rollback(self):
        """
        Test: Transaction rollback jika relocate file error
        
        Expected:
            - Document tidak ter-update
            - Version tidak increment
        """
        # Arrange
        document = DocumentFactory()
        user = UserFactory()
        new_category = CategoryFactory()
        
        original_category = document.category
        original_version = document.version
        
        form_data = {
            'category': new_category,
            'document_date': date.today()
        }
        
        # Act
        with patch('apps.archive.services.document_service.relocate_document_file') as mock_relocate:
            mock_relocate.side_effect = Exception("Relocate failed")
            
            with pytest.raises(Exception):
                DocumentService.update_document(
                    document=document,
                    form_data=form_data,
                    user=user
                )
        
        # Assert - Document should not be updated
        document.refresh_from_db()
        assert document.category == original_category
        assert document.version == original_version


# ==================== DELETE DOCUMENT TESTS ====================

@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.service
class TestDocumentServiceDelete:
    """
    Test DocumentService.delete_document()
    
    Scenarios:
        - ✅ Soft delete berhasil
        - ✅ is_deleted flag set
        - ✅ deleted_at timestamp set
        - ✅ Activity logged
    """
    
    def test_delete_document_success(self):
        """
        Test: Soft delete document berhasil
        
        Expected:
            - is_deleted = True
            - deleted_at timestamp set
            - Document masih ada di database
        """
        # Arrange
        document = DocumentFactory()
        user = UserFactory()
        
        # Act
        deleted_doc = DocumentService.delete_document(
            document=document,
            user=user
        )
        
        # Assert
        deleted_doc.refresh_from_db()
        assert deleted_doc.is_deleted is True
        assert deleted_doc.deleted_at is not None
        assert isinstance(deleted_doc.deleted_at, timezone.datetime) # type: ignore
        
        # Verify document masih exist di DB (soft delete)
        assert Document.objects.filter(id=deleted_doc.id).exists() # type: ignore
    
    def test_delete_document_activity_logged(self):
        """
        Test: Activity log created saat delete
        
        Expected:
            - DocumentActivity record created
            - action_type = 'delete'
        """
        # Arrange
        document = DocumentFactory()
        user = UserFactory()
        
        initial_count = DocumentActivity.objects.count()
        
        # Act
        DocumentService.delete_document(
            document=document,
            user=user
        )
        
        # Assert
        assert DocumentActivity.objects.count() == initial_count + 1
        
        activity = DocumentActivity.objects.latest('created_at')
        assert activity.action_type == 'delete'
        assert activity.document == document
        assert activity.user == user
        assert 'dihapus' in activity.description.lower() # type: ignore


# ==================== GET ACTIVE DOCUMENTS TESTS ====================

@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.service
class TestDocumentServiceGetActive:
    """
    Test DocumentService.get_active_documents()
    
    Scenarios:
        - ✅ Get all active documents
        - ✅ Filter by category
        - ✅ Filter by date range
        - ✅ Search filter
        - ✅ Exclude deleted documents
    """
    
    def test_get_active_documents_all(self):
        """
        Test: Get semua active documents
        
        Expected:
            - Return only is_deleted=False
            - Ordered by date descending
        """
        # Arrange
        doc1 = DocumentFactory()
        doc2 = DocumentFactory()
        deleted_doc = DocumentFactory(is_deleted=True)
        
        # Act
        documents = DocumentService.get_active_documents()
        
        # Assert
        assert documents.count() == 2
        assert doc1 in documents
        assert doc2 in documents
        assert deleted_doc not in documents
    
    def test_get_active_documents_filter_by_category(self):
        """
        Test: Filter documents by category
        
        Expected:
            - Return only documents dari category tersebut
            - Include documents dari child categories
        """
        # Arrange
        parent = ParentCategoryFactory(name='Belanjaan', slug='belanjaan')
        cat_atk = CategoryFactory(name='ATK', slug='atk', parent=parent)
        cat_konsumsi = CategoryFactory(name='Konsumsi', slug='konsumsi', parent=parent)
        
        doc_atk = DocumentFactory(category=cat_atk)
        doc_konsumsi = DocumentFactory(category=cat_konsumsi)
        
        # Act
        filters = {'category': cat_atk}
        documents = DocumentService.get_active_documents(filters)
        
        # Assert
        assert documents.count() == 1
        assert doc_atk in documents
        assert doc_konsumsi not in documents
    
    def test_get_active_documents_filter_by_date_range(self):
        """
        Test: Filter documents by date range
        
        Expected:
            - Return documents within date range
        """
        # Arrange
        today = date.today()
        doc_today = DocumentFactory(document_date=today)
        doc_yesterday = DocumentFactory(document_date=today - timedelta(days=1))
        doc_last_week = DocumentFactory(document_date=today - timedelta(days=7))
        
        # Act
        filters = {
            'date_from': today - timedelta(days=2),
            'date_to': today
        }
        documents = DocumentService.get_active_documents(filters)
        
        # Assert
        assert documents.count() == 2
        assert doc_today in documents
        assert doc_yesterday in documents
        assert doc_last_week not in documents
    
    def test_get_active_documents_search(self):
        """
        Test: Search documents by keyword
        
        Expected:
            - Search dalam category name
            - Search dalam file name
        """
        # Arrange
        cat_atk = CategoryFactory(name='ATK', slug='atk')
        cat_konsumsi = CategoryFactory(name='Konsumsi', slug='konsumsi')
        
        doc_atk = DocumentFactory(category=cat_atk)
        doc_konsumsi = DocumentFactory(category=cat_konsumsi)
        
        # Act
        filters = {'search': 'ATK'}
        documents = DocumentService.get_active_documents(filters)
        
        # Assert
        assert documents.count() >= 1
        assert doc_atk in documents