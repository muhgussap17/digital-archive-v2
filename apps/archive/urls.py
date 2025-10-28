from django.urls import path
from . import views

app_name = 'archive'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Document CRUD
    path('documents/', views.document_list, name='document_list'),
    path('documents/<int:document_id>/', views.document_detail, name='document_detail'),
    path('documents/<int:document_id>/preview/', views.document_preview, name='document_preview'),
    path('documents/<int:document_id>/download/', views.document_download, name='document_download'),
    path('documents/<int:document_id>/update/', views.document_update, name='document_update'),
    path('documents/<int:document_id>/delete/', views.document_delete, name='document_delete'),
    
    # Upload
    path('upload/', views.document_upload, name='document_upload'),
    path('upload/spd/', views.spd_upload, name='spd_upload'),
    
    # Category filtering
    path('category/<slug:category_slug>/', views.category_documents, name='category_documents'),
    
    # Search
    path('search/', views.search_documents, name='search_documents'),
]