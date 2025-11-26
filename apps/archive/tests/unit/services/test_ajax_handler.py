"""
Modul: tests/unit/services/test_ajax_handler.py
Fungsi: Unit tests untuk AjaxHandler

Test Coverage:
    - is_ajax() - AJAX detection
    - success_redirect() - Success response dengan redirect
    - success_data() - Success response dengan data
    - error() - Error response
    - form_response() - Form HTML response
    - handle_ajax_or_redirect() - Smart handler

Test Strategy:
    - Test response format
    - Test JSON structure
    - Test status codes
    - Test message handling

Run Tests:
    pytest apps/archive/tests/unit/services/test_ajax_handler.py -v
"""

import json
from unittest.mock import Mock, patch

import pytest
from django.http import JsonResponse
from django.test import RequestFactory
from django import forms

from apps.archive.services import AjaxHandler
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.base import SessionBase

def attach_dummy_session(request):
    request.session = SessionBase()


# ==================== AJAX DETECTION TESTS ====================

@pytest.mark.unit
@pytest.mark.ajax
class TestAjaxDetection:
    """
    Test AjaxHandler.is_ajax()
    
    Scenarios:
        - ✅ Detect AJAX request
        - ✅ Detect non-AJAX request
    """
    
    def test_is_ajax_true(self):
        """
        Test: Detect AJAX request correctly
        
        Expected:
            - Return True untuk request dengan X-Requested-With header
        """
        # Arrange
        factory = RequestFactory()
        request = factory.get('/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        # Act
        result = AjaxHandler.is_ajax(request)
        
        # Assert
        assert result is True
    
    def test_is_ajax_false(self):
        """
        Test: Detect non-AJAX request
        
        Expected:
            - Return False untuk request tanpa X-Requested-With
        """
        # Arrange
        factory = RequestFactory()
        request = factory.get('/')
        
        # Act
        result = AjaxHandler.is_ajax(request)
        
        # Assert
        assert result is False


# ==================== SUCCESS REDIRECT TESTS ====================

@pytest.mark.unit
@pytest.mark.ajax
class TestSuccessRedirect:
    """
    Test AjaxHandler.success_redirect()
    
    Scenarios:
        - ✅ Basic success redirect
        - ✅ With Django messages
        - ✅ Response structure
        - ✅ Status code
    """
    
    def test_success_redirect_basic(self):
        """
        Test: Basic success redirect response
        
        Expected:
            - Return JsonResponse
            - success = True
            - Include message
            - Include redirect_url
        """
        # Act
        response = AjaxHandler.success_redirect(
            message='Operation successful',
            url='archive:document_list'
        )
        
        # Assert
        assert isinstance(response, JsonResponse)
        
        data = json.loads(response.content)
        assert data['success'] is True
        assert data['message'] == 'Operation successful'
        assert 'redirect_url' in data
        assert '/documents/' in data['redirect_url']
    
    def test_success_redirect_status_code(self):
        """
        Test: Success redirect dengan custom status code
        
        Expected:
            - Status code sesuai parameter
        """
        # Act
        response = AjaxHandler.success_redirect(
            message='Created',
            url='archive:document_list',
            status_code=201
        )
        
        # Assert
        assert response.status_code == 201
    
    @patch('apps.archive.services.ajax_handler.messages')
    def test_success_redirect_with_django_messages(self, mock_messages):
        """
        Test: Success redirect add message ke Django messages framework
        
        Expected:
            - messages.success() dipanggil
        """
        # Arrange
        factory = RequestFactory()
        request = factory.get('/')
        
        # Act
        AjaxHandler.success_redirect(
            message='Success!',
            url='archive:document_list',
            request=request
        )
        
        # Assert
        mock_messages.success.assert_called_once_with(request, 'Success!')


# ==================== SUCCESS DATA TESTS ====================

@pytest.mark.unit
@pytest.mark.ajax
class TestSuccessData:
    """
    Test AjaxHandler.success_data()
    
    Scenarios:
        - ✅ Success response dengan data
        - ✅ Without data
        - ✅ Response structure
    """
    
    def test_success_data_with_data(self):
        """
        Test: Success response dengan additional data
        
        Expected:
            - Return JsonResponse
            - Include data dict
        """
        # Arrange
        data_payload = {
            'total': 100,
            'items': [1, 2, 3]
        }
        
        # Act
        response = AjaxHandler.success_data(
            message='Data loaded',
            data=data_payload
        )
        
        # Assert
        assert isinstance(response, JsonResponse)
        
        data = json.loads(response.content)
        assert data['success'] is True
        assert data['message'] == 'Data loaded'
        assert data['data'] == data_payload
    
    def test_success_data_without_data(self):
        """
        Test: Success response tanpa additional data
        
        Expected:
            - No 'data' key in response
        """
        # Act
        response = AjaxHandler.success_data(
            message='Success'
        )
        
        # Assert
        data = json.loads(response.content)
        assert data['success'] is True
        assert 'data' not in data


# ==================== ERROR RESPONSE TESTS ====================

@pytest.mark.unit
@pytest.mark.ajax
class TestErrorResponse:
    """
    Test AjaxHandler.error()
    
    Scenarios:
        - ✅ Basic error response
        - ✅ With form errors
        - ✅ Status code 400
        - ✅ Django messages integration
    """
    
    def test_error_basic(self):
        """
        Test: Basic error response
        
        Expected:
            - success = False
            - Include error message
            - Status 400
        """
        # Act
        response = AjaxHandler.error(
            message='Operation failed'
        )
        
        # Assert
        assert isinstance(response, JsonResponse)
        assert response.status_code == 400
        
        data = json.loads(response.content)
        assert data['success'] is False
        assert data['message'] == 'Operation failed'
    
    def test_error_with_form_errors(self):
        """
        Test: Error response dengan form errors
        
        Expected:
            - Include 'errors' dict
        """
        # Arrange
        form_errors = {
            'field1': ['This field is required'],
            'field2': ['Invalid value']
        }
        
        # Act
        response = AjaxHandler.error(
            message='Validation failed',
            errors=form_errors
        )
        
        # Assert
        data = json.loads(response.content)
        assert 'errors' in data
        assert data['errors'] == form_errors
    
    @patch('apps.archive.services.ajax_handler.messages')
    def test_error_with_django_messages(self, mock_messages):
        """
        Test: Error add message ke Django messages
        
        Expected:
            - messages.error() dipanggil
        """
        # Arrange
        factory = RequestFactory()
        request = factory.get('/')
        
        # Act
        AjaxHandler.error(
            message='Error occurred',
            request=request
        )
        
        # Assert
        mock_messages.error.assert_called_once_with(request, 'Error occurred')


# ==================== FORM RESPONSE TESTS ====================

@pytest.mark.unit
@pytest.mark.ajax
class TestFormResponse:
    """
    Test AjaxHandler.form_response()
    
    Scenarios:
        - ✅ Valid form (GET request)
        - ✅ Invalid form (POST request)
        - ✅ HTML rendering
        - ✅ Response structure
    """
    
    def test_form_response_valid(self):
        """
        Test: Form response untuk GET request (empty form)
        
        Expected:
            - success = True
            - Include rendered HTML
        """
        # Arrange
        class TestForm(forms.Form):
            name = forms.CharField()
        
        form = TestForm()
        
        # Act
        with patch('apps.archive.services.ajax_handler.render_to_string') as mock_render:
            mock_render.return_value = '<form>...</form>'
            
            response = AjaxHandler.form_response(
                form=form,
                template='test.html',
                context={'test': 'value'},
                is_valid=True
            )
        
        # Assert
        assert isinstance(response, JsonResponse)
        
        data = json.loads(response.content)
        assert data['success'] is True
        assert 'html' in data
        assert data['html'] == '<form>...</form>'
    
    def test_form_response_invalid(self):
        """
        Test: Form response untuk POST invalid (form with errors)
        
        Expected:
            - success = False
            - Include errors
            - Include rendered HTML dengan errors
        """
        # Arrange
        class TestForm(forms.Form):
            name = forms.CharField(required=True)
        
        form = TestForm(data={})  # Empty data, akan invalid
        form.is_valid()  # Trigger validation
        
        # Act
        with patch('apps.archive.services.ajax_handler.render_to_string') as mock_render:
            mock_render.return_value = '<form class="has-errors">...</form>'
            
            response = AjaxHandler.form_response(
                form=form,
                template='test.html',
                is_valid=False
            )
        
        # Assert
        data = json.loads(response.content)
        assert data['success'] is False
        assert 'errors' in data
        assert 'html' in data


# ==================== HANDLE AJAX OR REDIRECT TESTS ====================

@pytest.mark.unit
@pytest.mark.ajax
class TestHandleAjaxOrRedirect:
    """
    Test AjaxHandler.handle_ajax_or_redirect()
    
    Scenarios:
        - ✅ AJAX success
        - ✅ AJAX error
        - ✅ Non-AJAX success
        - ✅ Non-AJAX error
    """
    
    def test_handle_ajax_success(self):
        """
        Test: Handle AJAX request dengan success
        
        Expected:
            - Return JsonResponse
            - Redirect URL included
        """
        # Arrange
        factory = RequestFactory()
        request = factory.get('/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        attach_dummy_session(request)

        setattr(request, '_messages', FallbackStorage(request))

        # Act
        response = AjaxHandler.handle_ajax_or_redirect(
            request=request,
            success=True,
            message='Success',
            redirect_url='archive:document_list'
        )
        
        # Assert
        assert isinstance(response, JsonResponse)
        
        data = json.loads(response.content)
        assert data['success'] is True
    
    def test_handle_ajax_error(self):
        """
        Test: Handle AJAX request dengan error
        
        Expected:
            - Return JsonResponse dengan success=False
        """
        # Arrange
        factory = RequestFactory()
        request = factory.get('/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        attach_dummy_session(request)

        setattr(request, '_messages', FallbackStorage(request))
        
        # Act
        response = AjaxHandler.handle_ajax_or_redirect(
            request=request,
            success=False,
            message='Error',
            redirect_url='archive:document_list',
            errors={'field': ['error']}
        )
        
        # Assert
        assert isinstance(response, JsonResponse)
        
        data = json.loads(response.content)
        assert data['success'] is False
    
    @patch('apps.archive.services.ajax_handler.redirect')
    @patch('apps.archive.services.ajax_handler.messages')
    def test_handle_non_ajax_success(self, mock_messages, mock_redirect):
        """
        Test: Handle non-AJAX request dengan success
        
        Expected:
            - Return redirect response
            - Success message added
        """
        # Arrange
        factory = RequestFactory()
        request = factory.get('/')
        
        # Act
        AjaxHandler.handle_ajax_or_redirect(
            request=request,
            success=True,
            message='Success',
            redirect_url='archive:document_list'
        )
        
        # Assert
        mock_messages.success.assert_called_once()
        mock_redirect.assert_called_once()
    
    @patch('apps.archive.services.ajax_handler.redirect')
    @patch('apps.archive.services.ajax_handler.messages')
    def test_handle_non_ajax_error(self, mock_messages, mock_redirect):
        """
        Test: Handle non-AJAX request dengan error
        
        Expected:
            - Return redirect response
            - Error message added
        """
        # Arrange
        factory = RequestFactory()
        request = factory.get('/')
        
        # Act
        AjaxHandler.handle_ajax_or_redirect(
            request=request,
            success=False,
            message='Error occurred',
            redirect_url='archive:document_list'
        )
        
        # Assert
        mock_messages.error.assert_called_once()
        mock_redirect.assert_called_once()


# ==================== DETAIL RESPONSE TESTS ====================

@pytest.mark.unit
@pytest.mark.ajax
class TestDetailResponse:
    """
    Test AjaxHandler.detail_response()
    
    Scenarios:
        - ✅ Detail data response
        - ✅ Custom status code
    """
    
    def test_detail_response(self):
        """
        Test: Detail response dengan data dict
        
        Expected:
            - Return JsonResponse
            - Data structure preserved
        """
        # Arrange
        detail_data = {
            'success': True,
            'document_name': 'Test Document',
            'detail_html': '<div>Details</div>'
        }
        
        # Act
        response = AjaxHandler.detail_response(detail_data)
        
        # Assert
        assert isinstance(response, JsonResponse)
        assert response.status_code == 200
        
        data = json.loads(response.content)
        assert data == detail_data
    
    def test_detail_response_custom_status(self):
        """
        Test: Detail response dengan custom status code
        
        Expected:
            - Status code sesuai parameter
        """
        # Act
        response = AjaxHandler.detail_response(
            data={'test': 'data'},
            status_code=201
        )
        
        # Assert
        assert response.status_code == 201