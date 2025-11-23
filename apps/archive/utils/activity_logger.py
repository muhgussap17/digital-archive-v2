"""
Modul: utils/activity_logger.py
Fungsi: Activity logging utilities untuk audit trail

Berisi fungsi-fungsi untuk:
    - Log document activities (create, view, download, update, delete)
    - Extract client information dari request (IP, User Agent)
    - Build activity log entries

Implementasi Standar:
    - Mengikuti PEP 8 naming conventions
    - Type hints untuk semua fungsi
    - Menggunakan constants untuk activity types
    - Proper error handling untuk network info extraction

Catatan Pemeliharaan:
    - Semua activity logging harus melalui fungsi di module ini
    - Jangan log sensitive information (passwords, tokens, etc)
    - Activity types harus match dengan model choices
    
Dependencies:
    - apps.archive.models: DocumentActivity model
    - apps.archive.constants: Activity type constants
    - Django request object
"""

from typing import Optional
from django.http import HttpRequest

from apps.archive.models import DocumentActivity

from ..constants import (
    CLIENT_IP_HEADER,
    CLIENT_IP_FALLBACK,
    USER_AGENT_HEADER,
    ACTIVITY_TYPES,
)


def extract_client_ip(request: HttpRequest) -> Optional[str]:
    """
    Extract client IP address dari HTTP request
    
    Menghandle proxy headers (X-Forwarded-For) untuk mendapatkan
    real client IP, bukan proxy IP.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        Client IP address string, atau None jika tidak ditemukan
        
    Examples:
        >>> # Direct connection
        >>> ip = extract_client_ip(request)
        >>> print(ip)
        '192.168.1.100'
        
        >>> # Behind proxy
        >>> # X-Forwarded-For: 203.0.113.1, 198.51.100.1
        >>> ip = extract_client_ip(request)
        >>> print(ip)
        '203.0.113.1'
    
    Implementasi Standar:
        - Check X-Forwarded-For header first (untuk proxy)
        - Fallback ke REMOTE_ADDR (untuk direct connection)
        - Return first IP jika ada multiple proxies
        
    Catatan Pemeliharaan:
        - X-Forwarded-For bisa di-spoof, jangan untuk security critical
        - Untuk logging/analytics saja
        - Consider privacy regulations (GDPR, etc)
    """
    x_forwarded_for = request.META.get(CLIENT_IP_HEADER)
    
    if x_forwarded_for:
        # X-Forwarded-For bisa berisi multiple IPs (client, proxy1, proxy2)
        # Ambil yang pertama (real client)
        ip = x_forwarded_for.split(',')[0].strip()
        return ip
    
    # Fallback ke REMOTE_ADDR
    return request.META.get(CLIENT_IP_FALLBACK)


def extract_user_agent(request: HttpRequest) -> str:
    """
    Extract User Agent string dari HTTP request
    
    User Agent berisi informasi tentang browser/client yang digunakan.
    Berguna untuk analytics dan debugging.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        User Agent string, atau empty string jika tidak ada
        
    Examples:
        >>> ua = extract_user_agent(request)
        >>> print(ua)
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...'
    
    Implementasi Standar:
        - Return empty string jika header tidak ada
        - Jangan truncate untuk full information
        
    Catatan Pemeliharaan:
        - User Agent string bisa sangat panjang (500+ chars)
        - Model field harus TextField, bukan CharField
        - Consider truncate jika perlu save space
    """
    return request.META.get(USER_AGENT_HEADER, '')


def log_document_activity(
    document,
    user,
    action_type: str,
    description: Optional[str] = None,
    request: Optional[HttpRequest] = None
) -> 'DocumentActivity':
    """
    Log aktivitas dokumen untuk audit trail
    
    Mencatat semua aktivitas yang dilakukan pada dokumen:
    create, view, download, update, delete.
    
    Args:
        document: Document instance yang di-action
        user: User instance yang melakukan action
        action_type: Tipe action ('create', 'view', 'download', 'update', 'delete')
        description: Optional deskripsi tambahan
        request: Optional HttpRequest untuk capture IP dan User Agent
        
    Returns:
        DocumentActivity instance yang baru dibuat
        
    Raises:
        ValueError: Jika action_type tidak valid
        
    Examples:
        >>> # Basic logging
        >>> activity = log_document_activity(
        ...     document=doc,
        ...     user=request.user,
        ...     action_type='create'
        ... )
        
        >>> # With description dan request info
        >>> activity = log_document_activity(
        ...     document=doc,
        ...     user=request.user,
        ...     action_type='update',
        ...     description='Updated document metadata',
        ...     request=request
        ... )
    
    Implementasi Standar:
        - Validate action_type terhadap ACTIVITY_TYPES
        - Extract IP dan User Agent jika request provided
        - Store all info untuk comprehensive audit trail
        
    Catatan Pemeliharaan:
        - Dipanggil dari views setelah setiap document operation
        - Jangan log sensitive data di description
        - action_type harus match dengan DocumentActivity.ACTION_CHOICES
        - Consider async logging untuk high-traffic scenarios
    """
    from ..models import DocumentActivity
    
    # Validate action_type
    if action_type not in ACTIVITY_TYPES:
        raise ValueError(
            f"Invalid action_type '{action_type}'. "
            f"Must be one of: {', '.join(ACTIVITY_TYPES)}"
        )
    
    # Build activity data
    activity_data = {
        'document': document,
        'user': user,
        'action_type': action_type,
        'description': description or '',
    }
    
    # Extract request info jika ada
    if request:
        activity_data['ip_address'] = extract_client_ip(request)
        activity_data['user_agent'] = extract_user_agent(request)
    
    # Create activity log
    return DocumentActivity.objects.create(**activity_data)