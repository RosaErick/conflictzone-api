"""
URL configuration for ConflictZone API project.
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('documentation/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('', include('api.urls')),
]
