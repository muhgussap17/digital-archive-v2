"""
Modul: tests/unit/forms/test_mixins.py
Fungsi: Unit tests untuk form mixins

Test Coverage:
    - DateFieldMixin
    - DateRangeFieldMixin
    - DateRangeValidationMixin
    - FileFieldMixin
    - EmployeeFieldMixin
    - DestinationFieldMixin
    - CategoryFieldMixin

Run Tests:
    pytest apps/archive/tests/unit/forms/test_mixins.py -v
"""

import pytest
from datetime import date, timedelta
from django import forms

from apps.archive.forms.mixins import (
    DateFieldMixin,
    DateRangeFieldMixin,
    DateRangeValidationMixin,
    FileFieldMixin,
    EmployeeFieldMixin,
    DestinationFieldMixin,
    CategoryFieldMixin,
)
from apps.archive.tests.factories import (
    EmployeeFactory,
    CategoryFactory,
    ParentCategoryFactory,
)


@pytest.mark.unit
@pytest.mark.forms
class TestDateFieldMixin:
    """Test DateFieldMixin"""
    
    def test_adds_document_date_field(self):
        """Test: Mixin adds document_date field"""
        class TestForm(DateFieldMixin, forms.Form):
            pass
        
        form = TestForm()
        assert 'document_date' in form.fields
        assert isinstance(form.fields['document_date'], forms.DateField)
    
    def test_validates_future_date(self):
        """Test: Reject future dates"""
        class TestForm(DateFieldMixin, forms.Form):
            pass
        
        tomorrow = date.today() + timedelta(days=1)
        form = TestForm(data={'document_date': tomorrow})
        
        assert not form.is_valid()
        assert 'document_date' in form.errors
    
    def test_accepts_today(self):
        """Test: Accept today's date"""
        class TestForm(DateFieldMixin, forms.Form):
            pass
        
        form = TestForm(data={'document_date': date.today()})
        assert form.is_valid()


@pytest.mark.unit
@pytest.mark.forms
class TestDateRangeFieldMixin:
    """Test DateRangeFieldMixin"""
    
    def test_adds_start_and_end_date_fields(self):
        """Test: Mixin adds start_date and end_date"""
        class TestForm(DateRangeFieldMixin, forms.Form):
            pass
        
        form = TestForm()
        assert 'start_date' in form.fields
        assert 'end_date' in form.fields


@pytest.mark.unit
@pytest.mark.forms
class TestDateRangeValidationMixin:
    """Test DateRangeValidationMixin"""
    
    def test_validates_end_after_start(self):
        """Test: end_date must be >= start_date"""
        class TestForm(DateRangeFieldMixin, DateRangeValidationMixin, forms.Form):
            pass
        
        today = date.today()
        form = TestForm(data={
            'start_date': today,
            'end_date': today - timedelta(days=1)
        })
        
        assert not form.is_valid()
        assert 'end_date' in form.errors


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.forms
class TestEmployeeFieldMixin:
    """Test EmployeeFieldMixin"""
    
    def test_adds_employee_field(self):
        """Test: Mixin adds employee field"""
        class TestForm(EmployeeFieldMixin, forms.Form):
            pass
        
        form = TestForm()
        assert 'employee' in form.fields
    
    def test_filters_active_employees_only(self):
        """Test: Only show active employees"""
        active_emp = EmployeeFactory(is_active=True)
        inactive_emp = EmployeeFactory(is_active=False)
        
        class TestForm(EmployeeFieldMixin, forms.Form):
            pass
        
        form = TestForm()
        queryset = form.fields['employee'].queryset # type: ignore
        
        assert active_emp in queryset
        assert inactive_emp not in queryset


# Add more mixin tests...