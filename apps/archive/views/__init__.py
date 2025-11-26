"""
Modul: views/__init__.py
Fungsi: Public API untuk views dengan backward compatibility

Re-export semua views untuk:
    - Backward compatibility dengan urls.py
    - Clean imports
    - Single source of truth

Usage di urls.py:
    from .views import document_create, dashboard, ...
    # Atau
    from . import views
    urlpatterns = [path('', views.dashboard), ...]
"""

# Dashboard & List Views
from .dashboard_views import (
    dashboard,
    document_list,
    spd_list,
    search_documents,
)

# Test Views
from .testing_views import (
    test,
)

# Document CRUD Views (Refactored)
from .document_views import (
    document_create,
    document_update,
    document_delete,
)

# SPD CRUD Views (Refactored)
from .spd_views import (
    spd_create,
    spd_update,
    spd_delete,
)

# Action Views
from .action_views import (
    document_detail,
    document_activities,
    document_download,
    document_preview,
)

# API Views (DRF)
from .api_views import (
    DocumentViewSet,
    CategoryViewSet,
    SPDViewSet,
    dashboard_stats_api,
)

__all__ = [
    # Dashboard & List
    'dashboard',
    'document_list',
    'spd_list',
    'search_documents',

    # Testing
    'test',
    
    # Document CRUD
    'document_create',
    'document_update',
    'document_delete',
    
    # SPD CRUD
    'spd_create',
    'spd_update',
    'spd_delete',
    
    # Actions
    'document_detail',
    'document_activities',
    'document_download',
    'document_preview',
    
    # API
    'DocumentViewSet',
    'CategoryViewSet',
    'SPDViewSet',
    'dashboard_stats_api',
]