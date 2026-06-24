import logging
from datetime import timedelta

import requests
from django.conf import settings
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from . import selectors
from .models import IngestionRun
from .schemas import (
    by_city_schema,
    density_schema,
    filters_schema,
    fogo_cruzado_health_schema,
    health_schema,
    monthly_schema,
    occurrences_schema,
    stats_schema,
    timeseries_schema,
)
from .serializers import (
    DensityQuerySerializer,
    OccurrenceQuerySerializer,
    OccurrenceSerializer,
    PaginationQuerySerializer,
)

logger = logging.getLogger(__name__)


# --- ingestion freshness ---------------------------------------------------

def _last_ingestion():
    return (
        IngestionRun.objects.exclude(finished_at__isnull=True)
        .filter(status__in=[IngestionRun.SUCCESS, IngestionRun.PARTIAL])
        .order_by('-finished_at')
        .first()
    )


def _stale_response():
    """503 when there is no usable ingestion yet or the data is too old.

    Honest failure: we never return an empty list to mask a broken pipeline.
    """
    last = _last_ingestion()
    if last is None:
        return Response({'error': 'no successful ingestion yet; data unavailable'}, status=503)
    age = timezone.now() - last.finished_at
    if age > timedelta(hours=settings.INGESTION_MAX_AGE_HOURS):
        hours = int(age.total_seconds() // 3600)
        return Response({'error': f'data is stale (last ingestion {hours}h ago)'}, status=503)
    return None


def _parse_filters(request):
    """Validate query params -> filters dict, or return (None, 400 Response)."""
    s = OccurrenceQuerySerializer(data=request.GET)
    if not s.is_valid():
        return None, Response(s.errors, status=400)
    return s.validated_data, None


# --- health ----------------------------------------------------------------

@health_schema
@api_view(['GET'])
def health_view(request):
    last = _last_ingestion()
    body = {'status': 'ok', 'lastIngestion': None}
    if last:
        age = timezone.now() - last.finished_at
        body['lastIngestion'] = {
            'status': last.status,
            'finishedAt': last.finished_at,
            'ageHours': round(age.total_seconds() / 3600, 1),
            'fetched': last.fetched,
        }
    return Response(body)


@fogo_cruzado_health_schema
@api_view(['GET'])
def fogo_cruzado_health_view(request):
    """Probe the external provider (operational check, not a data path)."""
    try:
        response = requests.post(
            'https://api-service.fogocruzado.org.br/api/v2/auth/login',
            json={
                'email': settings.FOGO_CRUZADO_EMAIL,
                'password': settings.FOGO_CRUZADO_PASSWORD,
            },
            timeout=10,
        )
        if response.status_code in (200, 201):
            return Response({
                'status': 'online',
                'message': 'Fogo Cruzado API is operational',
                'statusCode': response.status_code,
            })
        return Response({
            'status': 'error',
            'message': f'Fogo Cruzado API returned status {response.status_code}',
            'statusCode': response.status_code,
        }, status=503)
    except requests.exceptions.Timeout:
        return Response({'status': 'offline', 'message': 'request timed out', 'statusCode': None},
                        status=503)
    except requests.exceptions.ConnectionError:
        return Response({'status': 'offline', 'message': 'could not connect', 'statusCode': None},
                        status=503)


# --- data ------------------------------------------------------------------

@occurrences_schema
@api_view(['GET'])
def occurrences_view(request):
    filters, err = _parse_filters(request)
    if err:
        return err
    page_s = PaginationQuerySerializer(data=request.GET)
    if not page_s.is_valid():
        return Response(page_s.errors, status=400)
    if stale := _stale_response():
        return stale

    page = page_s.validated_data['page']
    take = page_s.validated_data['take']
    qs = selectors.filtered_occurrences(filters).order_by('-occurred_at')
    total = qs.count()
    start = (page - 1) * take
    items = qs[start:start + take]

    return Response({
        'data': OccurrenceSerializer(items, many=True).data,
        'pagination': {
            'page': page,
            'take': take,
            'total': total,
            'pages': (total + take - 1) // take if take else 0,
        },
    })


@density_schema
@api_view(['GET'])
def density_view(request):
    """Grid density (PostGIS) as GeoJSON — scales the map without shipping every point."""
    s = DensityQuerySerializer(data=request.GET)
    if not s.is_valid():
        return Response(s.errors, status=400)
    if stale := _stale_response():
        return stale
    filters = s.validated_data
    qs = selectors.filtered_occurrences(filters)
    return Response(selectors.density_grid(qs, filters['cell']))


@stats_schema
@api_view(['GET'])
def stats_view(request):
    filters, err = _parse_filters(request)
    if err:
        return err
    if stale := _stale_response():
        return stale
    return Response(selectors.stats(selectors.filtered_occurrences(filters)))


@monthly_schema
@api_view(['GET'])
def monthly_view(request):
    """Monthly breakdown — kept as an alias of timeseries(month) for the frontend."""
    filters, err = _parse_filters(request)
    if err:
        return err
    if stale := _stale_response():
        return stale
    rows = selectors.timeseries(selectors.filtered_occurrences(filters), 'month')
    # ponytail: same query, just rename `period` -> `month` (YYYY-MM) to keep the contract.
    data = [
        {'month': r['period'][:7], 'incidents': r['incidents'],
         'fatalities': r['fatalities'], 'injuries': r['injuries']}
        for r in rows
    ]
    return Response({'data': data})


@timeseries_schema
@api_view(['GET'])
def timeseries_view(request):
    filters, err = _parse_filters(request)
    if err:
        return err
    granularity = request.GET.get('granularity', 'day')
    if granularity not in ('day', 'week', 'month'):
        return Response({'granularity': 'must be one of day, week, month'}, status=400)
    if stale := _stale_response():
        return stale
    rows = selectors.timeseries(selectors.filtered_occurrences(filters), granularity)
    return Response({'granularity': granularity, 'data': rows})


@by_city_schema
@api_view(['GET'])
def by_city_view(request):
    filters, err = _parse_filters(request)
    if err:
        return err
    if stale := _stale_response():
        return stale
    return Response({'data': selectors.breakdown(selectors.filtered_occurrences(filters), 'city')})


@filters_schema
@api_view(['GET'])
def filters_view(request):
    filters, err = _parse_filters(request)
    if err:
        return err
    if stale := _stale_response():
        return stale
    return Response(selectors.filter_options(selectors.filtered_occurrences(filters)))
