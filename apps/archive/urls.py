from django.urls import path
from .views import *

app_name = 'archive'

urlpatterns = [
    # Dashboard
    path('', dashboard, name='dashboard'),
    path('test/', test, name='test'),
    
    # Search Documents
    path('search/', search_documents, name='document_search'), 

    # Document CRUD (Modal/AJAX endpoints)
    path('documents/', document_list, name='document_list'),
    path('documents/category/<slug:category_slug>/', document_list, name='document_list_by_category'),
    path('documents/create/', document_create, name='document_create'), # Upload via modal
    path('documents/<int:pk>/update/', document_update, name='document_update'), # Edit via modal
    path('documents/<int:pk>/delete/', document_delete, name='document_delete'), # Soft delete action

    # SPD CRUD (Modal/AJAX endpoints)
    path('spd/', spd_list, name='spd_list'),
    path('spd/create/', spd_create, name='spd_create'), # Upload via modal
    path('spd/<int:pk>/update/', spd_update, name='spd_update'), # Edit via modal
    path('spd/<int:pk>/delete/', spd_delete, name='spd_delete'), # Soft delete action

    # Document Detail & Activities (untuk right panel)
    path('documents/<int:pk>/detail/', document_detail, name='document_detail'),
    path('documents/<int:pk>/activities/', document_activities, name='document_activities'),

    # Document Actions (View, Preview, Download)
    path('documents/<int:pk>/preview/', document_preview, name='document_preview'), # Preview action
    path('documents/<int:pk>/download/', document_download, name='document_download'), # Download action
]