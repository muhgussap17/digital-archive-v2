"""
Modul: tests/conftest.py
Fungsi: Shared fixtures dan configuration untuk pytest

Berisi:
    - Database fixtures (users, categories, employees)
    - File fixtures (PDF files untuk testing)
    - Request factories
    - Reusable test data

Implementasi Standar:
    - Mengikuti pytest best practices
    - Fixtures dengan proper scope (function, module, session)
    - Cleanup otomatis setelah test
    - Type hints untuk better IDE support

Cara Penggunaan:
    # Di test file
    def test_something(user, category, sample_pdf):
        # Fixtures otomatis tersedia
        document = Document.objects.create(
            file=sample_pdf,
            category=category,
            created_by=user
        )
"""

import os
import tempfile
from datetime import date, timedelta
from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory

from apps.archive.models import DocumentCategory, Employee, Document, SPDDocument

User = get_user_model()


# ==================== DATABASE FIXTURES ====================

@pytest.fixture
def user(db):
    """
    Create regular user untuk testing
    
    Returns:
        User instance dengan credentials:
            - username: testuser
            - password: testpass123
            - is_staff: False
    
    Usage:
        def test_something(user):
            assert user.username == 'testuser'
    """
    return User.objects.create_user( # type: ignore
        username='testuser',
        email='test@example.com',
        password='testpass123',
        full_name='Test User'
    )


@pytest.fixture
def staff_user(db):
    """
    Create staff user untuk testing staff-only views
    
    Returns:
        User instance dengan is_staff=True
    """
    return User.objects.create_user( # type: ignore
        username='staffuser',
        email='staff@example.com',
        password='testpass123',
        full_name='Staff User',
        is_staff=True
    )


@pytest.fixture
def superuser(db):
    """
    Create superuser untuk testing admin functionality
    
    Returns:
        User instance dengan is_superuser=True
    """
    return User.objects.create_superuser( # type: ignore
        username='admin',
        email='admin@example.com',
        password='adminpass123',
        full_name='Admin User'
    )


@pytest.fixture
def parent_category_belanjaan(db):
    """
    Create parent category 'Belanjaan'
    
    Returns:
        DocumentCategory instance (parent)
    """
    return DocumentCategory.objects.create(
        name='Belanjaan',
        slug='belanjaan',
        icon='fa-shopping-cart',
        parent=None
    )


@pytest.fixture
def parent_category_spd(db):
    """
    Create parent category 'SPD'
    
    Returns:
        DocumentCategory instance (parent)
    """
    return DocumentCategory.objects.create(
        name='SPD',
        slug='spd',
        icon='fa-plane',
        parent=None
    )


@pytest.fixture
def category_atk(db, parent_category_belanjaan):
    """
    Create subcategory 'ATK' under Belanjaan
    
    Returns:
        DocumentCategory instance (child)
    """
    return DocumentCategory.objects.create(
        name='ATK',
        slug='atk',
        icon='fa-pen',
        parent=parent_category_belanjaan
    )


@pytest.fixture
def category_konsumsi(db, parent_category_belanjaan):
    """
    Create subcategory 'Konsumsi' under Belanjaan
    
    Returns:
        DocumentCategory instance (child)
    """
    return DocumentCategory.objects.create(
        name='Konsumsi',
        slug='konsumsi',
        icon='fa-utensils',
        parent=parent_category_belanjaan
    )


@pytest.fixture
def employee(db):
    """
    Create employee untuk SPD testing
    
    Returns:
        Employee instance dengan data dummy
    """
    return Employee.objects.create(
        nip='198501012010011001',
        name='John Doe',
        position='Staff Administrasi',
        department='Bagian Umum',
        is_active=True
    )


@pytest.fixture
def employee_2(db):
    """
    Create second employee untuk testing multiple employees
    
    Returns:
        Employee instance
    """
    return Employee.objects.create(
        nip='198601012011012002',
        name='Jane Smith',
        position='Kepala Bagian',
        department='Bagian Keuangan',
        is_active=True
    )


# ==================== FILE FIXTURES ====================

@pytest.fixture
def sample_pdf():
    """
    Create valid PDF file untuk testing upload
    
    Returns:
        SimpleUploadedFile dengan PDF signature
    
    Usage:
        def test_upload(sample_pdf):
            response = client.post(url, {'file': sample_pdf})
    """
    # Minimal valid PDF
    pdf_content = b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/Resources <<\n/Font <<\n/F1 4 0 R\n>>\n>>\n/MediaBox [0 0 612 792]\n/Contents 5 0 R\n>>\nendobj\n4 0 obj\n<<\n/Type /Font\n/Subtype /Type1\n/BaseFont /Helvetica\n>>\nendobj\n5 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n(Test PDF) Tj\nET\nendstream\nendobj\nxref\n0 6\n0000000000 65535 f\n0000000015 00000 n\n0000000068 00000 n\n0000000125 00000 n\n0000000287 00000 n\n0000000366 00000 n\ntrailer\n<<\n/Size 6\n/Root 1 0 R\n>>\nstartxref\n458\n%%EOF'
    
    return SimpleUploadedFile(
        name='test_document.pdf',
        content=pdf_content,
        content_type='application/pdf'
    )


@pytest.fixture
def large_pdf():
    """
    Create PDF file yang melebihi size limit (untuk testing validation)
    
    Returns:
        SimpleUploadedFile dengan size > 10MB
    """
    # 11MB of data
    large_content = b'%PDF-1.4\n' + b'X' * (11 * 1024 * 1024)
    
    return SimpleUploadedFile(
        name='large_document.pdf',
        content=large_content,
        content_type='application/pdf'
    )


@pytest.fixture
def invalid_pdf():
    """
    Create file yang bukan PDF (untuk testing validation)
    
    Returns:
        SimpleUploadedFile dengan content bukan PDF
    """
    return SimpleUploadedFile(
        name='not_a_pdf.pdf',
        content=b'This is not a PDF file',
        content_type='application/pdf'
    )


@pytest.fixture
def temp_media_root(settings, tmp_path):
    """
    Create temporary media directory untuk testing file operations
    
    Automatically cleanup setelah test selesai.
    
    Usage:
        def test_file_upload(temp_media_root):
            # Files akan tersimpan di temp directory
            # Auto cleanup setelah test
    """
    media_root = tmp_path / "media"
    media_root.mkdir()
    settings.MEDIA_ROOT = str(media_root)
    return media_root


# ==================== REQUEST FIXTURES ====================

@pytest.fixture
def request_factory():
    """
    Django RequestFactory untuk testing views
    
    Returns:
        RequestFactory instance
    
    Usage:
        def test_view(request_factory, user):
            request = request_factory.get('/path/')
            request.user = user
            response = my_view(request)
    """
    return RequestFactory()


@pytest.fixture
def ajax_request_factory(request_factory):
    """
    RequestFactory dengan AJAX headers
    
    Returns:
        RequestFactory GET request dengan AJAX headers
    
    Usage:
        def test_ajax_view(ajax_request_factory):
            request = ajax_request_factory
            request.user = user
            response = my_view(request)
    """
    def _make_ajax_request(method='get', path='/', data=None):
        factory = RequestFactory()
        request_method = getattr(factory, method)
        request = request_method(
            path,
            data=data or {},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        return request
    
    return _make_ajax_request


# ==================== MODEL FIXTURES ====================

@pytest.fixture
def document(db, user, category_atk, sample_pdf):
    """
    Create sample Document instance
    
    Returns:
        Document instance dengan file
    
    Usage:
        def test_something(document):
            assert document.category.slug == 'atk'
    """
    return Document.objects.create(
        file=sample_pdf,
        document_date=date.today(),
        category=category_atk,
        created_by=user
    )


@pytest.fixture
def spd_document(db, staff_user, parent_category_spd, employee, sample_pdf):
    """
    Create sample SPD Document dengan metadata lengkap
    
    Returns:
        Tuple (Document, SPDDocument)
    
    Usage:
        def test_spd(spd_document):
            document, spd = spd_document
            assert spd.employee.name == 'John Doe'
    """
    document = Document.objects.create(
        file=sample_pdf,
        document_date=date.today(),
        category=parent_category_spd,
        created_by=staff_user
    )
    
    spd = SPDDocument.objects.create(
        document=document,
        employee=employee,
        destination='jakarta',
        destination_other='',
        start_date=date.today(),
        end_date=date.today() + timedelta(days=2)
    )
    
    return document, spd


# ==================== FORM DATA FIXTURES ====================

@pytest.fixture
def valid_document_form_data(category_atk):
    """
    Valid form data untuk DocumentForm
    
    Returns:
        Dict dengan form data yang valid
    
    Usage:
        def test_form(valid_document_form_data, sample_pdf):
            form = DocumentForm(
                data=valid_document_form_data,
                files={'file': sample_pdf}
            )
            assert form.is_valid()
    """
    return {
        'category': category_atk.id,
        'document_date': date.today().strftime('%Y-%m-%d'),
    }


@pytest.fixture
def valid_spd_form_data(employee):
    """
    Valid form data untuk SPDDocumentForm
    
    Returns:
        Dict dengan form data yang valid
    
    Usage:
        def test_spd_form(valid_spd_form_data, sample_pdf):
            form = SPDDocumentForm(
                data=valid_spd_form_data,
                files={'file': sample_pdf}
            )
            assert form.is_valid()
    """
    today = date.today()
    return {
        'document_date': today.strftime('%Y-%m-%d'),
        'employee': employee.id,
        'destination': 'jakarta',
        'destination_other': '',
        'start_date': today.strftime('%Y-%m-%d'),
        'end_date': (today + timedelta(days=2)).strftime('%Y-%m-%d'),
    }


# ==================== SESSION SCOPE FIXTURES ====================

@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    """
    Setup database untuk testing
    
    Runs once per test session untuk performance
    """
    pass


# ==================== CLEANUP FIXTURES ====================

@pytest.fixture(autouse=True)
def cleanup_uploaded_files(temp_media_root):
    """
    Auto cleanup uploaded files setelah setiap test
    
    autouse=True: Runs automatically untuk setiap test
    """
    yield
    # Cleanup logic runs after test
    if temp_media_root.exists():
        import shutil
        shutil.rmtree(temp_media_root, ignore_errors=True)