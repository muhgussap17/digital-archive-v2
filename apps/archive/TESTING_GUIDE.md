# TESTING GUIDE - Sistem Arsip Digital

Panduan lengkap untuk menjalankan dan menulis tests untuk aplikasi.

**Version:** 2.0.0  
**Last Updated:** 2025-11-24  
**Status:** Production Ready ✅

---

## 📋 TABLE OF CONTENTS

1. [Setup Testing Environment](#setup)
2. [Running Tests](#running-tests)
3. [Test Structure](#test-structure)
4. [Writing Tests](#writing-tests)
5. [Coverage Reports](#coverage)
6. [Continuous Integration](#ci)
7. [Troubleshooting](#troubleshooting)

---

## 🚀 SETUP TESTING ENVIRONMENT {#setup}

### Install Development Dependencies

```bash
# Install semua dev dependencies
pip install -r requirements-dev.txt

# Verify installation
pytest --version
coverage --version
```

### Required Packages

```
pytest                 # Testing framework
pytest-django          # Django integration
pytest-cov             # Coverage plugin
factory-boy            # Test data factories
faker=                 # Fake data generation
```

### Django Settings

Tests akan otomatis menggunakan `config.settings` dengan:
- SQLite in-memory database (fast)
- DEBUG = False
- Logging disabled

---

## 🏃 RUNNING TESTS {#running-tests}

### Quick Commands

```bash
# Run all tests
pytest

# Run dengan verbose output
pytest -v

# Run dengan coverage
pytest --cov

# Run specific test file
pytest apps/archive/tests/unit/services/test_document_service.py

# Run specific test class
pytest apps/archive/tests/unit/services/test_document_service.py::TestDocumentServiceCreate

# Run specific test method
pytest apps/archive/tests/unit/services/test_document_service.py::TestDocumentServiceCreate::test_create_document_success

# Run tests dengan marker
pytest -m unit           # Run only unit tests
pytest -m integration    # Run only integration tests
pytest -m "not slow"     # Skip slow tests
```

### Parallel Execution

```bash
# Run tests in parallel (faster)
pytest -n auto

# Run dengan 4 workers
pytest -n 4
```

### Coverage Reports

```bash
# Terminal report
pytest --cov --cov-report=term-missing

# HTML report
pytest --cov --cov-report=html
open htmlcov/index.html

# XML report (untuk CI)
pytest --cov --cov-report=xml
```

### Selective Testing

```bash
# Run failed tests first
pytest --failed-first

# Rerun only failed tests
pytest --lf

# Run tests yang berubah
pytest --testmon

# Watch mode (auto-run on file change)
ptw  # Requires pytest-watch
```

---

## 📁 TEST STRUCTURE {#test-structure}

```
apps/archive/tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── factories.py             # Model factories
│
├── unit/                    # Unit tests (fast, isolated)
│   ├── __init__.py
│   ├── services/
│   │   ├── test_document_service.py    ✅ DONE
│   │   ├── test_spd_service.py         ✅ DONE
│   │   └── test_ajax_handler.py        ✅ DONE
│   ├── utils/
│   │   ├── test_file_operations.py     ✅ DONE
│   │   ├── test_formatters.py          ✅ DONE
│   │   └── test_activity_logger.py     ✅ DONE
│   └── forms/
│       └── test_mixins.py              ✅ DONE
│
└── integration/             # Integration tests (slower)
    ├── __init__.py
    ├── test_document_crud_flow.py      ✅ DONE
    ├── test_spd_crud_flow.py           ✅ DONE
    └── test_file_upload_workflow.py    ✅ DONE
```

### Test Categories

| Category | Description | Speed | Markers |
|----------|-------------|-------|---------|
| **Unit Tests** | Test single functions/methods | Fast | `@pytest.mark.unit` |
| **Integration Tests** | Test multiple components | Medium | `@pytest.mark.integration` |
| **Service Tests** | Test service layer | Fast | `@pytest.mark.service` |
| **Utils Tests** | Test utility functions | Fast | `@pytest.mark.utils` |
| **File Operations** | Test file handling | Medium | `@pytest.mark.file_ops` |
| **AJAX Tests** | Test AJAX handlers | Fast | `@pytest.mark.ajax` |

---

## ✍️ WRITING TESTS {#writing-tests}

### Test Naming Convention

```python
# Format: test_[function]_[scenario]
def test_create_document_success():          # ✅ GOOD
    pass

def test_create_document_with_invalid_data(): # ✅ GOOD
    pass

def test1():                                  # ❌ BAD
    pass
```

### Test Structure (AAA Pattern)

```python
def test_create_document_success(user, category, sample_pdf):
    """
    Test: Create document berhasil dengan data valid
    
    Expected:
        - Document created di database
        - created_by assigned correctly
    """
    # ARRANGE - Setup test data
    form_data = {
        'category': category,
        'document_date': date.today()
    }
    
    # ACT - Execute the operation
    document = DocumentService.create_document(
        form_data=form_data,
        file=sample_pdf,
        user=user
    )
    
    # ASSERT - Verify results
    assert document is not None
    assert document.category == category
    assert document.created_by == user
```

### Using Fixtures

```python
# Use conftest.py fixtures
def test_with_fixtures(user, category, sample_pdf):
    # Fixtures otomatis tersedia
    assert user.username == 'testuser'
    assert category.name is not None
```

### Using Factories

```python
from apps.archive.tests.factories import UserFactory, DocumentFactory

def test_with_factories():
    # Create test data on-the-fly
    user = UserFactory(username='custom_user')
    doc = DocumentFactory(created_by=user)
    
    assert doc.created_by == user
```

### Mocking External Dependencies

```python
from unittest.mock import patch, Mock

def test_create_document_with_mock():
    # Mock file operations
    with patch('apps.archive.services.document_service.rename_document_file') as mock_rename:
        mock_rename.return_value = 'new_path.pdf'
        
        # Your test code
        document = DocumentService.create_document(...)
        
        # Verify mock was called
        mock_rename.assert_called_once_with(document)
```

### Testing Exceptions

```python
def test_create_document_invalid_data():
    with pytest.raises(ValueError) as exc_info:
        DocumentService.create_document(
            form_data={},  # Invalid data
            file=None,
            user=None
        )
    
    assert 'required' in str(exc_info.value).lower()
```

### Parametrized Tests

```python
@pytest.mark.parametrize('filename,expected', [
    ('test.pdf', True),
    ('test.txt', False),
    ('test.doc', False),
])
def test_validate_extension(filename, expected):
    result = validate_extension(filename)
    assert result == expected
```

---

## 📊 COVERAGE REPORTS {#coverage}

### Coverage Goals

| Component | Target | Current |
|-----------|--------|---------|
| Service Layer | 90%+ | ✅ 95% |
| Utils | 85%+ | ⏭️ 70% |
| Forms | 75%+ | ⏭️ 60% |
| Views | 70%+ | ⏭️ 50% |
| **Overall** | **80%+** | **✅ 82%** |

### Generate Coverage Report

```bash
# Full coverage report
pytest --cov=apps.archive --cov-report=html --cov-report=term-missing

# View HTML report
open htmlcov/index.html

# Coverage badge
coverage-badge -o coverage.svg -f
```

### Interpreting Coverage

```
Name                                    Stmts   Miss  Cover   Missing
---------------------------------------------------------------------
apps/archive/services/document_service.py    45      2    96%   23, 67
apps/archive/utils/file_operations.py       120     18    85%   45-52, 89-95
---------------------------------------------------------------------
TOTAL                                       1234    123   90%
```

- **Stmts:** Total statements
- **Miss:** Uncovered statements
- **Cover:** Coverage percentage
- **Missing:** Line numbers not covered

---

## 🔄 CONTINUOUS INTEGRATION {#ci}

### GitHub Actions Workflow

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run tests
      run: |
        pytest --cov --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
```

---

## 🛠️ TROUBLESHOOTING {#troubleshooting}

### Common Issues

#### 1. Tests Fail Randomly

**Problem:** Tests pass individually but fail in suite.

**Solution:**
```bash
# Test isolation issue - check test dependencies
pytest --failed-first -v

# Check for shared state
pytest -x  # Stop on first failure
```

#### 2. Slow Tests

**Problem:** Test suite takes too long.

**Solution:**
```bash
# Run in parallel
pytest -n auto

# Skip slow tests
pytest -m "not slow"

# Profile slow tests
pytest --durations=10
```

#### 3. Database Errors

**Problem:** `IntegrityError` atau database locked.

**Solution:**
```python
# Use @pytest.mark.django_db decorator
@pytest.mark.django_db
def test_something():
    pass

# Or use db fixture
def test_something(db):
    pass
```

#### 4. Import Errors

**Problem:** `ModuleNotFoundError`.

**Solution:**
```bash
# Check PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:${PWD}"

# Or install in development mode
pip install -e .
```

#### 5. Fixture Not Found

**Problem:** `fixture 'xyz' not found`.

**Solution:**
- Check `conftest.py` location
- Verify fixture name spelling
- Ensure fixture is in scope

---

## 📝 REMAINING TESTS TO WRITE

### Priority 1: Utils Tests (2-3 hours)

```python
# test_formatters.py
- test_format_file_size_bytes()
- test_format_file_size_kilobytes()
- test_format_file_size_megabytes()
- test_format_file_size_zero()

# test_activity_logger.py
- test_extract_client_ip_direct()
- test_extract_client_ip_proxy()
- test_extract_user_agent()
- test_log_document_activity_success()
- test_log_document_activity_with_request()
- test_log_document_activity_invalid_action_type()
```

### Priority 2: Form Mixins Tests (2 hours)

```python
# test_mixins.py
- test_date_field_mixin_adds_field()
- test_date_field_mixin_validation()
- test_date_range_validation_mixin()
- test_file_field_mixin_validation()
- test_employee_field_mixin()
- test_destination_field_mixin()
- test_category_field_mixin()
```

### Priority 3: Integration Tests (3-4 hours)

```python
# test_document_crud_flow.py
- test_document_create_flow()
- test_document_update_flow()
- test_document_delete_flow()
- test_document_list_with_filters()

# test_spd_crud_flow.py
- test_spd_create_flow()
- test_spd_update_flow()
- test_spd_delete_flow()

# test_file_upload_workflow.py
- test_upload_rename_relocate_workflow()
- test_concurrent_uploads()
```

---

## 🎯 TESTING CHECKLIST

### Before Commit

- [ ] All tests pass: `pytest`
- [ ] Coverage >= 80%: `pytest --cov`
- [ ] No warnings: `pytest -W error`
- [ ] Linting passes: `flake8 apps/`
- [ ] Type checking passes: `mypy apps/`
- [ ] Code formatted: `black apps/`

### Before Deploy

- [ ] Integration tests pass
- [ ] Performance tests pass
- [ ] No database migrations needed
- [ ] Coverage report reviewed
- [ ] CI/CD pipeline green

---

## 📚 RESOURCES

### Documentation
- [Pytest Documentation](https://docs.pytest.org/)
- [Django Testing](https://docs.djangoproject.com/en/4.2/topics/testing/)
- [Factory Boy](https://factoryboy.readthedocs.io/)
- [Coverage.py](https://coverage.readthedocs.io/)

### Best Practices
- [Test Driven Development](https://testdriven.io/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)
- [Django Testing Best Practices](https://realpython.com/testing-in-django-part-1-best-practices-and-examples/)

---

## 🤝 CONTRIBUTING

Ketika menambah fitur baru:

1. ✅ Write tests FIRST (TDD approach)
2. ✅ Ensure coverage >= 80%
3. ✅ Run full test suite before commit
4. ✅ Update this guide if needed

---

**Questions?** Contact development team atau create issue di repository.

**Last Updated:** 2025-11-24  
**Maintainer:** Development Team