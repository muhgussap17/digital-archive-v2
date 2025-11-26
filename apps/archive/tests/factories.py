"""
Modul: tests/factories.py
Fungsi: Factory classes untuk generate test data

Menggunakan factory_boy untuk create model instances dengan data realistis.
Lebih flexible daripada fixtures untuk test cases yang complex.

Implementasi Standar:
    - Mengikuti factory_boy best practices
    - Faker untuk generate realistic data
    - LazyAttribute untuk computed fields
    - SubFactory untuk related objects

Cara Penggunaan:
    # Simple creation
    user = UserFactory()
    
    # Override attributes
    admin = UserFactory(is_staff=True)
    
    # Create batch
    users = UserFactory.create_batch(5)
    
    # Build tanpa save ke DB
    user = UserFactory.build()
"""

from datetime import date, timedelta

import factory
from factory.django import DjangoModelFactory
from faker import Faker

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.archive.models import (
    DocumentCategory,
    Employee,
    Document,
    SPDDocument,
    DocumentActivity
)

User = get_user_model()
fake = Faker('id_ID')  # Indonesian locale


# ==================== USER FACTORIES ====================

class UserFactory(DjangoModelFactory):
    """
    Factory untuk User model
    
    Attributes:
        username: Auto-generated unique username
        email: Auto-generated email
        full_name: Fake Indonesian name
        password: Default 'testpass123' (hashed)
        is_staff: False (override untuk staff users)
        is_active: True
    
    Usage:
        >>> user = UserFactory()
        >>> user.username
        'user_12345'
        
        >>> staff = UserFactory(is_staff=True)
        >>> staff.is_staff
        True
    """
    
    class Meta: # type: ignore
        model = User
        django_get_or_create = ('username',)
        skip_postgeneration_save = True
    
    username = factory.Sequence(lambda n: f'user_{n}') # type: ignore
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com') # type: ignore
    full_name = factory.Faker('name', locale='id_ID') # type: ignore
    is_staff = False
    is_active = True
    
    @factory.post_generation # type: ignore
    def password(obj, create, extracted, **kwargs):
        """Set password dengan proper hashing"""
        if create:
            obj.set_password(extracted or 'testpass123') # type: ignore
            obj.save() # type: ignore


class StaffUserFactory(UserFactory):
    """
    Factory untuk staff user
    
    Usage:
        >>> staff = StaffUserFactory()
        >>> staff.is_staff
        True
    """
    is_staff = True


class SuperUserFactory(UserFactory):
    """
    Factory untuk superuser
    
    Usage:
        >>> admin = SuperUserFactory()
        >>> admin.is_superuser
        True
    """
    is_staff = True
    is_superuser = True


# ==================== CATEGORY FACTORIES ====================

class ParentCategoryFactory(DjangoModelFactory):
    """
    Factory untuk parent DocumentCategory
    
    Usage:
        >>> category = ParentCategoryFactory(name='Belanjaan')
    """
    
    class Meta: # type: ignore
        model = DocumentCategory
        django_get_or_create = ('slug',)
    
    name = factory.Faker('word') # type: ignore
    slug = factory.LazyAttribute(lambda obj: obj.name.lower()) # type: ignore
    icon = 'fa-folder'
    parent = None


class CategoryFactory(DjangoModelFactory):
    """
    Factory untuk child DocumentCategory
    
    Usage:
        >>> parent = ParentCategoryFactory(name='Belanjaan', slug='belanjaan')
        >>> child = CategoryFactory(parent=parent, name='ATK', slug='atk')
    """
    
    class Meta: # type: ignore
        model = DocumentCategory
        django_get_or_create = ('slug',)
    
    name = factory.Faker('word') # type: ignore
    slug = factory.LazyAttribute(lambda obj: obj.name.lower()) # type: ignore
    icon = 'fa-file'
    parent = factory.SubFactory(ParentCategoryFactory) # type: ignore


# ==================== EMPLOYEE FACTORY ====================

class EmployeeFactory(DjangoModelFactory):
    """
    Factory untuk Employee model
    
    Attributes:
        nip: Auto-generated 18-digit NIP
        name: Fake Indonesian name
        position: Random position
        department: Random department
        is_active: True
    
    Usage:
        >>> employee = EmployeeFactory()
        >>> len(employee.nip)
        18
        
        >>> employees = EmployeeFactory.create_batch(5)
        >>> len(employees)
        5
    """
    
    class Meta: # type: ignore
        model = Employee
        django_get_or_create = ('nip',)
    
    nip = factory.Sequence(lambda n: f'{198501010000000000 + n:018d}') # type: ignore
    name = factory.Faker('name', locale='id_ID') # type: ignore
    position = factory.Faker('job', locale='id_ID') # type: ignore
    department = factory.Faker( # type: ignore
        'random_element',
        elements=['Bagian Umum', 'Bagian Keuangan', 'Bagian Kepegawaian']
    )
    is_active = True


# ==================== FILE FACTORY ====================

class PDFFileFactory(factory.Factory): # type: ignore
    """
    Factory untuk generate PDF file
    
    Returns:
        SimpleUploadedFile dengan valid PDF content
    
    Usage:
        >>> pdf = PDFFileFactory()
        >>> pdf.name
        'document.pdf'
    """
    
    class Meta: # type: ignore
        model = SimpleUploadedFile
    
    name = 'document.pdf'
    content_type = 'application/pdf'
    
    @factory.lazy_attribute # type: ignore
    def content(self):
        """Generate minimal valid PDF"""
        return b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/Resources <<\n/Font <<\n/F1 4 0 R\n>>\n>>\n/MediaBox [0 0 612 792]\n/Contents 5 0 R\n>>\nendobj\n4 0 obj\n<<\n/Type /Font\n/Subtype /Type1\n/BaseFont /Helvetica\n>>\nendobj\n5 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n(Test PDF) Tj\nET\nendstream\nendobj\nxref\n0 6\n0000000000 65535 f\n0000000015 00000 n\n0000000068 00000 n\n0000000125 00000 n\n0000000287 00000 n\n0000000366 00000 n\ntrailer\n<<\n/Size 6\n/Root 1 0 R\n>>\nstartxref\n458\n%%EOF'


# ==================== DOCUMENT FACTORY ====================

class DocumentFactory(DjangoModelFactory):
    """
    Factory untuk Document model
    
    Attributes:
        file: Auto-generated PDF
        document_date: Today's date
        category: Auto-generated child category
        created_by: Auto-generated user
        is_deleted: False
    
    Usage:
        >>> doc = DocumentFactory()
        >>> doc.file.name.endswith('.pdf')
        True
        
        >>> # With specific category
        >>> atk_category = CategoryFactory(name='ATK', slug='atk')
        >>> doc = DocumentFactory(category=atk_category)
    """
    
    class Meta: # type: ignore
        model = Document
    
    file = factory.LazyAttribute(lambda obj: PDFFileFactory()) # type: ignore
    document_date = factory.LazyFunction(date.today) # type: ignore
    category = factory.SubFactory(CategoryFactory) # type: ignore
    created_by = factory.SubFactory(UserFactory) # type: ignore
    is_deleted = False
    version = 1


# ==================== SPD DOCUMENT FACTORY ====================

class SPDDocumentFactory(DjangoModelFactory):
    """
    Factory untuk SPDDocument model
    
    Creates both Document dan SPDDocument dalam satu call.
    
    Attributes:
        document: Auto-generated Document dengan SPD category
        employee: Auto-generated Employee
        destination: Random destination
        start_date: Today
        end_date: +2 days
    
    Usage:
        >>> spd = SPDDocumentFactory()
        >>> spd.employee.name
        'John Doe'
        
        >>> # With specific employee
        >>> employee = EmployeeFactory(name='Jane Smith')
        >>> spd = SPDDocumentFactory(employee=employee)
        >>> spd.employee.name
        'Jane Smith'
    """
    
    class Meta: # type: ignore
        model = SPDDocument
    
    document = factory.SubFactory( # type: ignore
        DocumentFactory,
        category=factory.SubFactory( # type: ignore
            ParentCategoryFactory,
            name='SPD',
            slug='spd'
        )
    )
    employee = factory.SubFactory(EmployeeFactory) # type: ignore
    destination = factory.Faker( # type: ignore
        'random_element',
        elements=['jakarta', 'surabaya', 'bandung', 'yogyakarta', 'balikpapan']
    )
    destination_other = ''
    start_date = factory.LazyFunction(date.today) # type: ignore
    end_date = factory.LazyAttribute(lambda obj: obj.start_date + timedelta(days=2)) # type: ignore

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """
        Override untuk mengembalikan tuple (document, spd)
        """
        # 1. Buat SPDDocument (ini otomatis membuat Document melalui SubFactory)
        spd = super()._create(model_class, *args, **kwargs)

        # 2. Ambil objek Document yang sudah dibuat
        document = spd.document # Karena relasi OneToOneField terbalik: related_name='spd_info'

        # 3. WAJIB: return 2 nilai
        return document, spd # <-- Mengembalikan tuple iterable

    
# ==================== DOCUMENT ACTIVITY FACTORY ====================

class DocumentActivityFactory(DjangoModelFactory):
    """
    Factory untuk DocumentActivity model
    
    Attributes:
        document: Auto-generated Document
        user: Auto-generated User
        action_type: Random action
        description: Auto-generated description
    
    Usage:
        >>> activity = DocumentActivityFactory(action_type='create')
        >>> activity.action_type
        'create'
    """
    
    class Meta: # type: ignore
        model = DocumentActivity
    
    document = factory.SubFactory(DocumentFactory) # type: ignore
    user = factory.SubFactory(UserFactory) # type: ignore
    action_type = factory.Faker( # type: ignore
        'random_element',
        elements=['create', 'view', 'download', 'update', 'delete']
    )
    description = factory.LazyAttribute( # type: ignore
        lambda obj: f"Document {obj.action_type}d by {obj.user.username}"
    )
    ip_address = factory.Faker('ipv4') # type: ignore
    user_agent = 'Mozilla/5.0 (Test Browser)'


# ==================== BULK CREATION HELPERS ====================

def create_test_categories():
    """
    Helper untuk create standard test categories
    
    Returns:
        Dict dengan standard categories
    
    Usage:
        >>> categories = create_test_categories()
        >>> categories['atk'].name
        'ATK'
    """
    belanjaan = ParentCategoryFactory(name='Belanjaan', slug='belanjaan')
    spd_parent = ParentCategoryFactory(name='SPD', slug='spd')
    
    atk = CategoryFactory(
        name='ATK',
        slug='atk',
        parent=belanjaan
    )
    konsumsi = CategoryFactory(
        name='Konsumsi',
        slug='konsumsi',
        parent=belanjaan
    )
    bbm = CategoryFactory(
        name='BBM',
        slug='bbm',
        parent=belanjaan
    )
    
    return {
        'belanjaan': belanjaan,
        'spd': spd_parent,
        'atk': atk,
        'konsumsi': konsumsi,
        'bbm': bbm,
    }


def create_test_users():
    """
    Helper untuk create standard test users
    
    Returns:
        Dict dengan standard users
    
    Usage:
        >>> users = create_test_users()
        >>> users['staff'].is_staff
        True
    """
    return {
        'regular': UserFactory(username='testuser'),
        'staff': StaffUserFactory(username='staffuser'),
        'admin': SuperUserFactory(username='admin'),
    }


def create_test_employees():
    """
    Helper untuk create test employees
    
    Returns:
        List of Employee instances
    
    Usage:
        >>> employees = create_test_employees()
        >>> len(employees)
        3
    """
    return [
        EmployeeFactory(
            nip='198501012010011001',
            name='John Doe',
            position='Staff Administrasi'
        ),
        EmployeeFactory(
            nip='198601012011012002',
            name='Jane Smith',
            position='Kepala Bagian'
        ),
        EmployeeFactory(
            nip='198701012012013003',
            name='Bob Johnson',
            position='Sekretaris'
        ),
    ]