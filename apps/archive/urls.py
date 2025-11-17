from django.urls import path
from . import views

app_name = 'archive'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('test/', views.test, name='test'),
    
    # Search Documents
    path('search/', views.search_documents, name='document_search'), 

    # Document CRUD (Modal/AJAX endpoints)
    path('documents/', views.document_list, name='document_list'),
    path('documents/category/<slug:category_slug>/', views.document_list, name='document_list_by_category'),
    path('documents/create/', views.document_create, name='document_create'), # Upload via modal
    path('documents/<int:pk>/update/', views.document_update, name='document_update'), # Edit via modal
    path('documents/<int:pk>/delete/', views.document_delete, name='document_delete'), # Soft delete action

    # SPD CRUD (Modal/AJAX endpoints)
    path('spd/', views.spd_list, name='spd_list'),
    path('spd/create/', views.spd_create, name='spd_create'), # Upload via modal
    path('spd/<int:pk>/update/', views.spd_update, name='spd_update'), # Edit via modal
    path('spd/<int:pk>/delete/', views.spd_delete, name='spd_delete'), # Soft delete action

    # Document Detail & Activities (untuk right panel)
    path('documents/<int:pk>/detail/', views.document_detail, name='document_detail'),
    path('documents/<int:pk>/activities/', views.document_activities, name='document_activities'),

    # Document Actions (View, Preview, Download)
    path('documents/<int:pk>/preview/', views.document_preview, name='document_preview'), # Preview action
    path('documents/<int:pk>/download/', views.document_download, name='document_download'), # Download action
]