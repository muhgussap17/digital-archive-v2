"""
Modul: tests/unit/utils/test_activity_logger.py
Fungsi: Unit tests untuk activity logging utilities

Test Coverage:
    - extract_client_ip() - IP extraction
    - extract_user_agent() - User agent extraction
    - log_document_activity() - Activity logging

Run Tests:
    pytest apps/archive/tests/unit/utils/test_activity_logger.py -v
"""

import pytest
from django.test import RequestFactory

from apps.archive.utils import (
    extract_client_ip,
    extract_user_agent,
    log_document_activity,
)
from apps.archive.models import DocumentActivity
from apps.archive.tests.factories import DocumentFactory, UserFactory


@pytest.mark.unit
@pytest.mark.utils
class TestExtractClientIP:
    """Test extract_client_ip()"""
    
    def test_extract_ip_direct_connection(self):
        """Test: Extract IP dari direct connection"""
        factory = RequestFactory()
        request = factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.100'
        
        ip = extract_client_ip(request)
        assert ip == '192.168.1.100'
    
    def test_extract_ip_behind_proxy(self):
        """Test: Extract real client IP behind proxy"""
        factory = RequestFactory()
        request = factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '203.0.113.1, 198.51.100.1'
        request.META['REMOTE_ADDR'] = '10.0.0.1'
        
        ip = extract_client_ip(request)
        assert ip == '203.0.113.1'  # First IP in chain
    
    def test_extract_ip_no_header(self):
        """Test: Handle missing IP header"""
        factory = RequestFactory()
        request = factory.get('/')
        
        ip = extract_client_ip(request)
        assert ip is None or ip == '127.0.0.1'


@pytest.mark.unit
@pytest.mark.utils
class TestExtractUserAgent:
    """Test extract_user_agent()"""
    
    def test_extract_user_agent_present(self):
        """Test: Extract user agent when present"""
        factory = RequestFactory()
        request = factory.get('/')
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0 Test Browser'
        
        ua = extract_user_agent(request)
        assert ua == 'Mozilla/5.0 Test Browser'
    
    def test_extract_user_agent_missing(self):
        """Test: Handle missing user agent"""
        factory = RequestFactory()
        request = factory.get('/')
        
        ua = extract_user_agent(request)
        assert ua == ''


@pytest.mark.django_db
@pytest.mark.unit
@pytest.mark.utils
class TestLogDocumentActivity:
    """Test log_document_activity()"""
    
    def test_log_activity_success(self):
        """Test: Log activity successfully"""
        document = DocumentFactory()
        user = UserFactory()
        
        activity = log_document_activity(
            document=document,
            user=user,
            action_type='create',
            description='Test activity'
        )
        
        assert activity is not None
        assert activity.document == document
        assert activity.user == user
        assert activity.action_type == 'create'
    
    def test_log_activity_with_request(self):
        """Test: Log activity with request info"""
        document = DocumentFactory()
        user = UserFactory()
        
        factory = RequestFactory()
        request = factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.100'
        request.META['HTTP_USER_AGENT'] = 'Test Browser'
        
        activity = log_document_activity(
            document=document,
            user=user,
            action_type='view',
            request=request
        )
        
        assert activity.ip_address == '192.168.1.100'
        assert activity.user_agent == 'Test Browser'
    
    def test_log_activity_invalid_action_type(self):
        """Test: Reject invalid action type"""
        document = DocumentFactory()
        user = UserFactory()
        
        with pytest.raises(ValueError):
            log_document_activity(
                document=document,
                user=user,
                action_type='invalid_action'
            )