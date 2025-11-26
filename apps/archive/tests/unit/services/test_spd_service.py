"""
Modul: tests/unit/services/test_spd_service.py
Fungsi: Unit tests untuk SPDService

Test Coverage:
    - create_spd() - Create SPD dengan metadata
    - update_spd() - Update SPD metadata
    - delete_spd() - Soft delete SPD
    - get_active_spd_documents() - Query helper

Test Strategy:
    - Test Document + SPDDocument creation dalam 1 transaction
    - Mock file operations
    - Test SPD-specific validations
    - Test error handling

Run Tests:
    pytest apps/archive/tests/unit/services/test_spd_service.py -v
"""

from datetime import date, timedelta
from unittest.mock import patch

import pytest
from django.db import transaction

from apps.archive.models import Document, SPDDocument, DocumentActivity
from apps.archive.services import SPDService
from apps.archive.tests.factories import (
    UserFactory,
    StaffUserFactory,
    EmployeeFactory,
    ParentCategoryFactory,
    SPDDocumentFactory,
    PDFFileFactory,
)


# ==================== CREATE SPD TESTS ====================

@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.service
class TestSPDServiceCreate:
    """
    Test SPDService.create_spd()
    
    Scenarios:
        - ✅ Create SPD berhasil
        - ✅ Document dan SPDDocument created
        - ✅ Category assigned correctly (spd)
        - ✅ File rename dipanggil
        - ✅ Activity logged
    """
    
    def test_create_spd_success(self):
        """
        Test: Create SPD berhasil dengan data lengkap
        
        Expected:
            - Document created
            - SPDDocument created dengan OneToOne relation
            - Category = 'spd'
            - Activity logged
        """
        # Arrange
        user = StaffUserFactory()
        employee = EmployeeFactory(name='John Doe')
        pdf_file = PDFFileFactory()
        
        # Ensure SPD category exists
        spd_category = ParentCategoryFactory(name='SPD', slug='spd')
        
        today = date.today()
        form_data = {
            'file': pdf_file,
            'document_date': today,
            'employee': employee,
            'destination': 'jakarta',
            'destination_other': '',
            'start_date': today,
            'end_date': today + timedelta(days=2)
        }
        
        # Act
        with patch('apps.archive.services.spd_service.rename_document_file') as mock_rename:
            document = SPDService.create_spd(
                form_data=form_data,
                user=user
            )
        
        # Assert - Document created
        assert document is not None
        assert document.category.slug == 'spd'
        assert document.created_by == user
        assert document.document_date == today
        
        # Assert - SPDDocument created
        assert hasattr(document, 'spd_info')
        spd = document.spd_info # type: ignore
        assert spd.employee == employee
        assert spd.destination == 'jakarta'
        assert spd.start_date == today
        assert spd.end_date == today + timedelta(days=2)
        
        # Verify rename dipanggil
        mock_rename.assert_called_once_with(document)
    
    def test_create_spd_with_destination_other(self):
        """
        Test: Create SPD dengan destination='other'
        
        Expected:
            - destination_other field populated
            - get_destination_display_full() returns destination_other
        """
        # Arrange
        user = StaffUserFactory()
        employee = EmployeeFactory()
        pdf_file = PDFFileFactory()
        
        ParentCategoryFactory(name='SPD', slug='spd')
        
        today = date.today()
        form_data = {
            'file': pdf_file,
            'document_date': today,
            'employee': employee,
            'destination': 'other',
            'destination_other': 'Pontianak',
            'start_date': today,
            'end_date': today + timedelta(days=1)
        }
        
        # Act
        with patch('apps.archive.services.spd_service.rename_document_file'):
            document = SPDService.create_spd(
                form_data=form_data,
                user=user
            )
        
        # Assert
        spd = document.spd_info # type: ignore
        assert spd.destination == 'other'
        assert spd.destination_other == 'Pontianak'
        assert spd.get_destination_display_full() == 'Pontianak'
    
    def test_create_spd_activity_logged(self):
        """
        Test: Activity log created saat create SPD
        
        Expected:
            - DocumentActivity created
            - action_type = 'create'
            - Description includes employee name dan destination
        """
        # Arrange
        user = StaffUserFactory()
        employee = EmployeeFactory(name='Jane Smith')
        pdf_file = PDFFileFactory()
        
        ParentCategoryFactory(name='SPD', slug='spd')
        
        today = date.today()
        form_data = {
            'file': pdf_file,
            'document_date': today,
            'employee': employee,
            'destination': 'surabaya',
            'destination_other': '',
            'start_date': today,
            'end_date': today + timedelta(days=1)
        }
        
        initial_count = DocumentActivity.objects.count()
        
        # Act
        with patch('apps.archive.services.spd_service.rename_document_file'):
            document = SPDService.create_spd(
                form_data=form_data,
                user=user
            )
        
        # Assert
        assert DocumentActivity.objects.count() == initial_count + 1
        
        activity = DocumentActivity.objects.latest('created_at')
        assert activity.action_type == 'create'
        assert activity.document == document
        assert 'Jane Smith' in activity.description # type: ignore
        assert 'Surabaya' in activity.description or 'surabaya' in activity.description # type: ignore
    
    def test_create_spd_transaction_rollback(self):
        """
        Test: Transaction rollback jika SPDDocument creation fails
        
        Expected:
            - No Document created
            - No SPDDocument created
            - Atomic transaction
        """
        # Arrange
        user = StaffUserFactory()
        employee = EmployeeFactory()
        pdf_file = PDFFileFactory()
        
        ParentCategoryFactory(name='SPD', slug='spd')
        
        form_data = {
            'file': pdf_file,
            'document_date': date.today(),
            'employee': employee,
            'destination': 'jakarta',
            'destination_other': '',
            'start_date': date.today(),
            'end_date': date.today() + timedelta(days=1)
        }
        
        initial_doc_count = Document.objects.count()
        initial_spd_count = SPDDocument.objects.count()
        
        # Act - Mock rename untuk raise exception
        with patch('apps.archive.services.spd_service.rename_document_file') as mock_rename:
            mock_rename.side_effect = Exception("Rename failed")
            
            with pytest.raises(Exception):
                SPDService.create_spd(
                    form_data=form_data,
                    user=user
                )
        
        # Assert - Nothing should be created
        assert Document.objects.count() == initial_doc_count
        assert SPDDocument.objects.count() == initial_spd_count


# ==================== UPDATE SPD TESTS ====================

@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.service
class TestSPDServiceUpdate:
    """
    Test SPDService.update_spd()
    
    Scenarios:
        - ✅ Update SPD metadata berhasil
        - ✅ Document dan SPDDocument updated
        - ✅ Version increment
        - ✅ File relocate dipanggil
    """
    
    def test_update_spd_success(self):
        """
        Test: Update SPD metadata berhasil
        
        Expected:
            - Document date updated
            - SPD metadata updated
            - Version incremented
        """
        # Arrange
        document, spd = SPDDocumentFactory() # type: ignore
        user = StaffUserFactory()
        new_employee = EmployeeFactory(name='New Employee')
        new_date = date.today() - timedelta(days=1)
        
        original_version = document.version
        
        form_data = {
            'document_date': new_date,
            'employee': new_employee,
            'destination': 'bandung',
            'destination_other': '',
            'start_date': new_date,
            'end_date': new_date + timedelta(days=1)
        }
        
        # Act
        with patch('apps.archive.services.spd_service.relocate_document_file') as mock_relocate:
            updated_doc = SPDService.update_spd(
                document=document,
                form_data=form_data,
                user=user
            )
        
        # Assert - Document updated
        updated_doc.refresh_from_db()
        assert updated_doc.document_date == new_date
        assert updated_doc.version == original_version + 1
        
        # Assert - SPD updated
        spd.refresh_from_db()
        assert spd.employee == new_employee
        assert spd.destination == 'bandung'
        assert spd.start_date == new_date
        
        # Verify relocate dipanggil
        mock_relocate.assert_called_once_with(updated_doc)
    
    def test_update_spd_activity_logged(self):
        """
        Test: Activity log created saat update SPD
        
        Expected:
            - DocumentActivity created
            - action_type = 'update'
        """
        # Arrange
        document, spd = SPDDocumentFactory() # type: ignore
        user = StaffUserFactory()
        
        form_data = {
            'document_date': date.today(),
            'employee': spd.employee,
            'destination': 'yogyakarta',
            'destination_other': '',
            'start_date': date.today(),
            'end_date': date.today() + timedelta(days=1)
        }
        
        initial_count = DocumentActivity.objects.count()
        
        # Act
        with patch('apps.archive.services.spd_service.relocate_document_file'):
            SPDService.update_spd(
                document=document,
                form_data=form_data,
                user=user
            )
        
        # Assert
        assert DocumentActivity.objects.count() == initial_count + 1
        
        activity = DocumentActivity.objects.latest('created_at')
        assert activity.action_type == 'update'
        assert activity.document == document


# ==================== DELETE SPD TESTS ====================

@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.service
class TestSPDServiceDelete:
    """
    Test SPDService.delete_spd()
    
    Scenarios:
        - ✅ Soft delete SPD berhasil
        - ✅ SPDDocument tetap exist
        - ✅ Activity logged
    """
    
    def test_delete_spd_success(self):
        """
        Test: Soft delete SPD berhasil
        
        Expected:
            - Document.is_deleted = True
            - SPDDocument masih exist
        """
        # Arrange
        document, spd = SPDDocumentFactory() # type: ignore
        user = StaffUserFactory()
        
        # Act
        deleted_doc = SPDService.delete_spd(
            document=document,
            user=user
        )
        
        # Assert
        deleted_doc.refresh_from_db()
        assert deleted_doc.is_deleted is True
        assert deleted_doc.deleted_at is not None
        
        # SPDDocument should still exist
        assert SPDDocument.objects.filter(document=deleted_doc).exists()
    
    def test_delete_spd_activity_logged(self):
        """
        Test: Activity log created saat delete SPD
        
        Expected:
            - DocumentActivity created
            - action_type = 'delete'
        """
        # Arrange
        document, spd = SPDDocumentFactory() # type: ignore
        user = StaffUserFactory()
        
        initial_count = DocumentActivity.objects.count()
        
        # Act
        SPDService.delete_spd(
            document=document,
            user=user
        )
        
        # Assert
        assert DocumentActivity.objects.count() == initial_count + 1
        
        activity = DocumentActivity.objects.latest('created_at')
        assert activity.action_type == 'delete'
        assert activity.document == document


# ==================== GET ACTIVE SPD TESTS ====================

@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.service
class TestSPDServiceGetActive:
    """
    Test SPDService.get_active_spd_documents()
    
    Scenarios:
        - ✅ Get all active SPD
        - ✅ Filter by employee
        - ✅ Filter by destination
        - ✅ Search functionality
    """
    
    def test_get_active_spd_all(self):
        """
        Test: Get semua active SPD documents
        
        Expected:
            - Return only SPD documents
            - Exclude deleted
        """
        # Arrange
        spd_doc1, _ = SPDDocumentFactory() # type: ignore
        spd_doc2, _ = SPDDocumentFactory() # type: ignore
        
        # Create deleted SPD
        deleted_doc, _ = SPDDocumentFactory() # type: ignore
        deleted_doc.is_deleted = True
        deleted_doc.save()
        
        # Act
        documents = SPDService.get_active_spd_documents()
        
        # Assert
        assert documents.count() == 2
        assert spd_doc1 in documents
        assert spd_doc2 in documents
        assert deleted_doc not in documents
    
    def test_get_active_spd_filter_by_employee(self):
        """
        Test: Filter SPD by employee
        
        Expected:
            - Return only SPD dari employee tersebut
        """
        # Arrange
        employee1 = EmployeeFactory(name='John Doe')
        employee2 = EmployeeFactory(name='Jane Smith')
        
        spd_john, _ = SPDDocumentFactory(employee=employee1) # type: ignore
        spd_jane, _ = SPDDocumentFactory(employee=employee2) # type: ignore
        
        # Act
        filters = {'employee': employee1}
        documents = SPDService.get_active_spd_documents(filters)
        
        # Assert
        assert documents.count() == 1
        assert spd_john in documents
        assert spd_jane not in documents
    
    def test_get_active_spd_search(self):
        """
        Test: Search SPD by employee name atau destination
        
        Expected:
            - Search dalam employee name
            - Search dalam destination
        """
        # Arrange
        emp_jakarta = EmployeeFactory(name='Jakarta Employee')
        emp_surabaya = EmployeeFactory(name='Surabaya Employee')
        
        spd_jakarta, _ = SPDDocumentFactory( # type: ignore
            employee=emp_jakarta,
            destination='jakarta'
        )
        spd_surabaya, _ = SPDDocumentFactory( # type: ignore
            employee=emp_surabaya,
            destination='surabaya'
        )
        
        # Act
        filters = {'search': 'Jakarta'}
        documents = SPDService.get_active_spd_documents(filters)
        
        # Assert
        assert spd_jakarta in documents