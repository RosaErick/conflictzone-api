from django.urls import path
from .views import health_view, occurrences_view

urlpatterns = [
    path('health/', health_view, name='health'),
    path('occurrences/', occurrences_view, name='occurrences'),
]
