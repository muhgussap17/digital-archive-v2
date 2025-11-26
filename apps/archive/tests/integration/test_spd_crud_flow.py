"""
Modul: tests/integration/test_spd_crud_flow.py
Fungsi: Integration tests untuk complete SPD CRUD workflow

Test Scenarios:
    - Complete SPD create flow: form → service → 2 models → file rename
    - Complete SPD update flow: update both models → file relocate
    - Complete SPD delete flow: soft delete → preserve metadata
    - SPD list and filter: by employee, destination, date
    - SPD-specific validations: date range, destination_other

Integration Level:
    - Forms + Services + Utils + 2 Models (Document + SPDDocument)
    - Database transactions (atomic)
    - File operations with employee names
    - Activity logging

Run Tests:
    pytest apps/archive/tests/integration/test_spd_crud_flow.py -v
"""

import os
from datetime import date, timedelta
from django.test import TestCase, override_settings
import tempfile

from apps.archive.models import Document, SPDDocument, DocumentActivity
from apps.archive.forms import SPDDocumentForm, SPDDocumentUpdateForm
from apps.archive.services import SPDService
from apps.archive.tests.factories import (
    StaffUserFactory,
    EmployeeFactory,
    ParentCategoryFactory,
    SPDDocumentFactory,
    PDFFileFactory,
)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class SPDCRUDFlowTest(TestCase):
    """
    Integration tests untuk SPD CRUD workflow
    
    SPD involves 2 models:
        - Document (base model)
        - SPDDocument (metadata model)
    
    All operations must maintain consistency between both models.
    
    Setup:
        - Test database (transactional)
        - Temporary media directory
        - Test users, employees, SPD category
    """
    
    def setUp(self):
        """Setup test data"""
        # Create staff user
        self.staff_user = StaffUserFactory()
        
        # Create employees
        self.employee1 = EmployeeFactory(
            nip='198501012010011001',
            name='John Doe',
            position='Staff Administrasi'
        )
        self.employee2 = EmployeeFactory(
            nip='198601012011012002',
            name='Jane Smith',
            position='Kepala Bagian'
        )
        
        # Create SPD category
        self.spd_category = ParentCategoryFactory(
            name='SPD',
            slug='spd'
        )
        
        # Create test file
        self.pdf_file = PDFFileFactory()
    
    # ==================== CREATE FLOW TESTS ====================
    
    def test_complete_spd_create_flow(self):
        """
        Test: Complete SPD creation workflow
        
        Flow:
            1. User fills SPD form with employee and travel info
            2. Form validation passes
            3. Service creates Document + SPDDocument atomically
            4. File uploaded and renamed with employee name
            5. Activity logged
            6. Both models retrievable
        
        Expected:
            - Document created with spd category
            - SPDDocument created with OneToOne relation
            - File named: SPD_EmployeeName_Destination_Date.pdf
            - Activity logged
            - All metadata correct
        """
        # Step 1: Prepare form data
        # today = date.today()
        base_date = date.today() - timedelta(days=10)
        form_data = {
            'document_date': base_date.strftime('%Y-%m-%d'),
            'employee': self.employee1.id,
            'destination': 'jakarta',
            'destination_other': '',
            'start_date': base_date.strftime('%Y-%m-%d'),
            'end_date': (base_date + timedelta(days=2)).strftime('%Y-%m-%d'),
        }
        
        # Step 2: Validate form
        form = SPDDocumentForm(data=form_data, files={'file': self.pdf_file})
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")
        
        # Step 3: Create SPD via service
        document = SPDService.create_spd(
            form_data=form.cleaned_data,
            user=self.staff_user
        )
        
        # Step 4: Verify Document created
        self.assertIsNotNone(document)
        self.assertEqual(document.category.slug, 'spd')
        self.assertEqual(document.created_by, self.staff_user)
        self.assertEqual(document.document_date, base_date)
        
        # Step 5: Verify SPDDocument created
        self.assertTrue(hasattr(document, 'spd_info'))
        spd = document.spd_info # type: ignore
        
        self.assertEqual(spd.employee, self.employee1)
        self.assertEqual(spd.destination, 'jakarta')
        self.assertEqual(spd.start_date, base_date)
        self.assertEqual(spd.end_date, base_date + timedelta(days=2))
        
        # Step 6: Verify file naming convention
        filename = os.path.basename(document.file.name)
        self.assertIn('SPD', filename)
        self.assertIn('JohnDoe', filename)  # Employee name
        self.assertIn('Jakarta', filename)  # Destination
        self.assertIn(base_date.strftime('%Y-%m-%d'), filename)
        
        # Step 7: Verify activity logged
        activities = DocumentActivity.objects.filter(document=document)
        self.assertEqual(activities.count(), 1)
        
        activity = activities.first()
        self.assertEqual(activity.action_type, 'create') # type: ignore
        self.assertIn('John Doe', activity.description) # type: ignore
        self.assertIn('Jakarta', activity.description) # type: ignore
    
    def test_spd_create_with_destination_other(self):
        """
        Test: Create SPD dengan destination='other'
        
        Flow:
            1. User selects 'other' for destination
            2. User fills destination_other field
            3. Form validates destination_other required
            4. SPD created with custom destination
        
        Expected:
            - destination = 'other'
            - destination_other populated
            - Filename uses destination_other value
        """
        # today = date.today()
        base_date = date.today() - timedelta(days=5)
        form_data = {
            'document_date': base_date.strftime('%Y-%m-%d'),
            'employee': self.employee1.id,
            'destination': 'other',
            'destination_other': 'Pontianak',
            'start_date': base_date.strftime('%Y-%m-%d'),
            'end_date': (base_date + timedelta(days=1)).strftime('%Y-%m-%d'),
        }
        
        form = SPDDocumentForm(data=form_data, files={'file': self.pdf_file})
        self.assertTrue(form.is_valid())
        
        document = SPDService.create_spd(
            form_data=form.cleaned_data,
            user=self.staff_user
        )
        
        spd = document.spd_info # type: ignore
        self.assertEqual(spd.destination, 'other')
        self.assertEqual(spd.destination_other, 'Pontianak')
        self.assertEqual(spd.get_destination_display_full(), 'Pontianak')
        
        # Verify filename uses destination_other
        filename = os.path.basename(document.file.name)
        self.assertIn('Pontianak', filename)
    
    def test_spd_create_validation_date_range(self):
        """
        Test: SPD create with invalid date range
        
        Flow:
            1. User submits end_date < start_date
            2. Form validation fails
            3. No SPD created
        
        Expected:
            - Form invalid
            - Error on end_date field
        """
        today = date.today()
        form_data = {
            'document_date': today.strftime('%Y-%m-%d'),
            'employee': self.employee1.id,
            'destination': 'jakarta',
            'destination_other': '',
            'start_date': today.strftime('%Y-%m-%d'),
            'end_date': (today - timedelta(days=1)).strftime('%Y-%m-%d'),  # Invalid!
        }
        
        form = SPDDocumentForm(data=form_data, files={'file': self.pdf_file})
        
        # Form should be invalid
        self.assertFalse(form.is_valid())
        self.assertIn('end_date', form.errors)
    
    # ==================== UPDATE FLOW TESTS ====================
    
    def test_complete_spd_update_flow(self):
        """
        Test: Complete SPD update workflow
        
        Flow:
            1. SPD exists
            2. User updates employee, destination, dates
            3. Form validation passes
            4. Service updates both Document and SPDDocument
            5. File renamed/relocated with new info
            6. Version incremented
            7. Activity logged
        
        Expected:
            - Both models updated
            - File relocated with new name
            - Version incremented
            - Activity logged
        """
        # Step 1: Create initial SPD
        document, spd = SPDDocumentFactory( # type: ignore
            employee=self.employee1,
            destination='jakarta'
        )
        
        # Create physical file
        file_path = document.file.path
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'wb') as f:
            f.write(self.pdf_file.read())
        
        initial_version = document.version
        
        # Step 2: Prepare update data (change employee and destination)
        new_date = date.today() - timedelta(days=1)
        form_data = {
            'document_date': new_date.strftime('%Y-%m-%d'),
            'employee': self.employee2.id,  # Changed
            'destination': 'surabaya',  # Changed
            'destination_other': '',
            'start_date': new_date.strftime('%Y-%m-%d'),
            'end_date': new_date.strftime('%Y-%m-%d'),
        }
        
        # Step 3: Validate form
        form = SPDDocumentUpdateForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")
        
        # Step 4: Update via service
        updated_doc = SPDService.update_spd(
            document=document,
            form_data=form.cleaned_data,
            user=self.staff_user
        )
        
        # Step 5: Verify Document updated
        updated_doc.refresh_from_db()
        self.assertEqual(updated_doc.document_date, new_date)
        self.assertEqual(updated_doc.version, initial_version + 1)
        
        # Step 6: Verify SPDDocument updated
        spd.refresh_from_db()
        self.assertEqual(spd.employee, self.employee2)
        self.assertEqual(spd.destination, 'surabaya')
        
        # Step 7: Verify file renamed with new employee name
        new_filename = os.path.basename(updated_doc.file.name)
        self.assertIn('JaneSmith', new_filename)  # New employee
        self.assertIn('Surabaya', new_filename)  # New destination
        
        # Step 8: Verify activity logged
        activities = DocumentActivity.objects.filter(
            document=document,
            action_type='update'
        )
        self.assertGreater(activities.count(), 0)
    
    def test_spd_update_dates_only(self):
        """
        Test: Update SPD dates without changing employee
        
        Flow:
            1. Update start_date and end_date
            2. Employee and destination unchanged
            3. File renamed with new date
        
        Expected:
            - Dates updated
            - Employee unchanged
            - File date portion updated
        """
        # Create SPD
        document, spd = SPDDocumentFactory( # type: ignore
            employee=self.employee1,
            start_date=date(2024, 1, 15),
            end_date=date(2024, 1, 17)
        )
        
        # Update dates
        new_start = date(2024, 2, 10)
        new_end = date(2024, 2, 12)
        
        form_data = {
            'document_date': new_start.strftime('%Y-%m-%d'),
            'employee': self.employee1.id,  # Same
            'destination': spd.destination,  # Same
            'destination_other': '',
            'start_date': new_start.strftime('%Y-%m-%d'),
            'end_date': new_end.strftime('%Y-%m-%d'),
        }
        
        form = SPDDocumentUpdateForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        updated_doc = SPDService.update_spd(
            document=document,
            form_data=form.cleaned_data,
            user=self.staff_user
        )
        
        # Verify dates updated
        spd.refresh_from_db()
        self.assertEqual(spd.start_date, new_start)
        self.assertEqual(spd.end_date, new_end)
        self.assertEqual(spd.employee, self.employee1)  # Unchanged
    
    # ==================== DELETE FLOW TESTS ====================
    
    def test_complete_spd_delete_flow(self):
        """
        Test: Complete SPD soft delete workflow
        
        Flow:
            1. SPD exists (Document + SPDDocument)
            2. User triggers delete
            3. Service soft deletes Document
            4. SPDDocument preserved (OneToOne relation)
            5. Activity logged
            6. Not in active queries
        
        Expected:
            - Document.is_deleted = True
            - SPDDocument still exists
            - Activity logged
            - Not in get_active_spd_documents()
        """
        # Step 1: Create SPD
        document, spd = SPDDocumentFactory(employee=self.employee1) # type: ignore
        document_id = document.id
        spd_pk = spd.pk
        
        # Step 2: Delete via service
        deleted_doc = SPDService.delete_spd(
            document=document,
            user=self.staff_user
        )
        
        # Step 3: Verify Document soft deleted
        deleted_doc.refresh_from_db()
        self.assertTrue(deleted_doc.is_deleted)
        self.assertIsNotNone(deleted_doc.deleted_at)
        
        # Step 4: Verify SPDDocument still exists
        self.assertTrue(
            SPDDocument.objects.filter(document_id=document_id).exists()
        )
        
        # Step 5: Verify not in active queries
        active_spd = SPDService.get_active_spd_documents()
        self.assertNotIn(deleted_doc, active_spd)
        
        # Step 6: Verify activity logged
        activities = DocumentActivity.objects.filter(
            document=document,
            action_type='delete'
        )
        self.assertEqual(activities.count(), 1)
    
    # ==================== LIST AND FILTER FLOW TESTS ====================
    
    def test_spd_list_and_filter_flow(self):
        """
        Test: List SPD with various filters
        
        Flow:
            1. Create multiple SPDs (different employees, destinations)
            2. Query without filters
            3. Query filtered by employee
            4. Query filtered by destination
            5. Query with search
        
        Expected:
            - Filters work correctly
            - Only active SPDs returned
            - Deleted SPDs excluded
        """
        # Step 1: Create test SPDs
        spd1_doc, spd1 = SPDDocumentFactory( # type: ignore
            employee=self.employee1,
            destination='jakarta'
        )
        
        spd2_doc, spd2 = SPDDocumentFactory( # type: ignore
            employee=self.employee2,
            destination='surabaya'
        )
        
        spd3_doc, spd3 = SPDDocumentFactory( # type: ignore
            employee=self.employee1,
            destination='bandung'
        )
        
        # Create deleted SPD
        spd_deleted_doc, _ = SPDDocumentFactory(employee=self.employee1) # type: ignore
        spd_deleted_doc.is_deleted = True
        spd_deleted_doc.save()
        
        # Step 2: Get all active SPDs
        all_spd = SPDService.get_active_spd_documents()
        self.assertEqual(all_spd.count(), 3)
        self.assertNotIn(spd_deleted_doc, all_spd)
        
        # Step 3: Filter by employee
        emp1_spd = SPDService.get_active_spd_documents({
            'employee': self.employee1
        })
        self.assertEqual(emp1_spd.count(), 2)
        self.assertIn(spd1_doc, emp1_spd)
        self.assertIn(spd3_doc, emp1_spd)
        self.assertNotIn(spd2_doc, emp1_spd)
        
        # Step 4: Filter by destination
        jakarta_spd = SPDService.get_active_spd_documents({
            'destination': 'jakarta'
        })
        self.assertEqual(jakarta_spd.count(), 1)
        self.assertIn(spd1_doc, jakarta_spd)
        
        # Step 5: Search by employee name
        search_results = SPDService.get_active_spd_documents({
            'search': 'John Doe'
        })
        self.assertGreaterEqual(search_results.count(), 2)
        self.assertIn(spd1_doc, search_results)
    
    def test_spd_duration_calculation(self):
        """
        Test: SPD duration calculation
        
        Expected:
            - get_duration_days() returns correct number
            - Includes both start and end date
        """
        today = date.today()
        document, spd = SPDDocumentFactory( # type: ignore
            start_date=today,
            end_date=today + timedelta(days=2)
        )
        
        # Duration should be 3 days (includes both endpoints)
        self.assertEqual(spd.get_duration_days(), 3)
    
    # ==================== TRANSACTION TESTS ====================
    
    def test_spd_create_atomic_transaction(self):
        """
        Test: SPD creation is atomic (both models or none)
        
        Flow:
            1. Start SPD creation
            2. Document created
            3. SPDDocument creation fails
            4. Transaction rolled back
            5. No Document created
        
        Expected:
            - Transaction rollback works
            - No partial data
        """
        from unittest.mock import patch
        
        initial_doc_count = Document.objects.count()
        initial_spd_count = SPDDocument.objects.count()
        
        form_data = {
            'file': self.pdf_file,
            'document_date': date.today(),
            'employee': self.employee1,
            'destination': 'jakarta',
            'destination_other': '',
            'start_date': date.today(),
            'end_date': date.today() + timedelta(days=1),
        }
        
        # Mock SPDDocument.objects.create to fail
        with patch('apps.archive.services.spd_service.SPDDocument.objects.create') as mock_create:
            mock_create.side_effect = Exception("SPD creation failed")
            
            # Should raise exception
            with self.assertRaises(Exception):
                SPDService.create_spd(
                    form_data=form_data,
                    user=self.staff_user
                )
        
        # Verify no Document created (rollback worked)
        self.assertEqual(Document.objects.count(), initial_doc_count)
        self.assertEqual(SPDDocument.objects.count(), initial_spd_count)
    
    # ==================== EDGE CASES ====================
    
    def test_spd_with_special_characters_in_name(self):
        """
        Test: SPD dengan employee name yang punya special characters
        
        Expected:
            - Special characters removed from filename
            - File naming still correct
        """
        # Create employee with special characters
        special_emp = EmployeeFactory(
            name="O'Brien-Smith"
        )
        
        form_data = {
            'file': self.pdf_file,
            'document_date': date.today(),
            'employee': special_emp,
            'destination': 'jakarta',
            'destination_other': '',
            'start_date': date.today(),
            'end_date': date.today() + timedelta(days=1),
        }
        
        form = SPDDocumentForm(data=form_data, files={'file': self.pdf_file})
        
        if form.is_valid():
            document = SPDService.create_spd(
                form_data=form.cleaned_data,
                user=self.staff_user
            )
            
            # Verify filename has no special characters
            filename = os.path.basename(document.file.name)
            self.assertNotIn("'", filename)
            self.assertNotIn("-", filename)
            self.assertIn('OBrien', filename) or self.assertIn('Smith', filename) # type: ignore