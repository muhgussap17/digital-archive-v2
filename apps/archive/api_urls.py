from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'api'

# Create router
router = DefaultRouter()
router.register(r'documents', views.DocumentViewSet, basename='document')
router.register(r'categories', views.CategoryViewSet, basename='category')
router.register(r'spd', views.SPDViewSet, basename='spd')

urlpatterns = [
    # Router URLs
    path('', include(router.urls)),
    
    # Additional endpoints
    path('dashboard/stats/', views.dashboard_stats_api, name='dashboard_stats'),
    
    # Authentication
    path('auth/', include('rest_framework.urls', namespace='rest_framework')),
]