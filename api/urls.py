from django.urls import path

from .views import (
    by_city_view,
    by_neighborhood_view,
    by_type_view,
    density_view,
    filters_view,
    fogo_cruzado_health_view,
    health_view,
    monthly_view,
    occurrences_view,
    stats_view,
    timeseries_view,
)

urlpatterns = [
    path('health/', health_view, name='health'),
    path('health/fogo-cruzado/', fogo_cruzado_health_view, name='fogo-cruzado-health'),
    path('occurrences/', occurrences_view, name='occurrences'),
    path('occurrences/density/', density_view, name='density'),
    path('occurrences/stats/', stats_view, name='stats'),
    path('occurrences/monthly/', monthly_view, name='monthly'),
    path('occurrences/timeseries/', timeseries_view, name='timeseries'),
    path('occurrences/by-city/', by_city_view, name='by-city'),
    path('occurrences/by-neighborhood/', by_neighborhood_view, name='by-neighborhood'),
    path('occurrences/by-type/', by_type_view, name='by-type'),
    path('occurrences/filters/', filters_view, name='filters'),
]
