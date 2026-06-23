from collections import defaultdict
import requests
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .services.fogo_cruzado import FogoCruzadoService
from .schemas import (
    health_schema,
    fogo_cruzado_health_schema,
    occurrences_schema,
    stats_schema,
    monthly_schema,
    by_city_schema,
    filters_schema,
)


def parse_bool(value):
    """Parse boolean from query string."""
    if value is None:
        return None
    return value.lower() in ('true', '1', 'yes')


def parse_int(value, default=None):
    """Parse integer from query string."""
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def get_filters(request):
    """Extract filters from request query parameters."""
    return {
        'initialdate': request.GET.get('initialdate'),
        'finaldate': request.GET.get('finaldate'),
        'mainReason': request.GET.get('mainReason'),
        'typeOccurrence': request.GET.get('typeOccurrence'),
        # 'type' may be repeated (multi-select); getlist returns [] when absent.
        'type': request.GET.getlist('type') or None,
        'city': request.GET.get('city'),
        'policePresent': parse_bool(request.GET.get('policePresent')),
        'victimStatus': request.GET.get('victimStatus'),
    }


def get_pagination(request):
    """Extract pagination from request query parameters."""
    page = parse_int(request.GET.get('page'), 1)
    take = parse_int(request.GET.get('take'), 100)
    # Limit take to a reasonable max. The whole dataset is already fetched and
    # cached server-side, so a larger page lets the map/table cover a full month.
    take = min(take, 5000)
    return page, take


def paginate(data, page, take):
    """Apply pagination to data list."""
    start = (page - 1) * take
    end = start + take
    return data[start:end], len(data)


@health_schema
@api_view(['GET'])
def health_view(request):
    return Response("Health Check! Ok!")


@fogo_cruzado_health_schema
@api_view(['GET'])
def fogo_cruzado_health_view(request):
    """Check if the Fogo Cruzado external API is available."""
    try:
        url = "https://api-service.fogocruzado.org.br/api/v2/auth/login"
        credentials = {
            "email": settings.FOGO_CRUZADO_EMAIL,
            "password": settings.FOGO_CRUZADO_PASSWORD
        }
        response = requests.post(url, json=credentials, timeout=10)

        if response.status_code in (200, 201):
            return Response({
                'status': 'online',
                'message': 'Fogo Cruzado API is operational',
                'statusCode': response.status_code
            })
        else:
            return Response({
                'status': 'error',
                'message': f'Fogo Cruzado API returned status {response.status_code}',
                'statusCode': response.status_code
            }, status=503)

    except requests.exceptions.Timeout:
        return Response({
            'status': 'offline',
            'message': 'Fogo Cruzado API request timed out',
            'statusCode': None
        }, status=503)
    except requests.exceptions.ConnectionError:
        return Response({
            'status': 'offline',
            'message': 'Could not connect to Fogo Cruzado API',
            'statusCode': None
        }, status=503)
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e),
            'statusCode': None
        }, status=503)


@occurrences_schema
@api_view(['GET'])
def occurrences_view(request):
    try:
        filters = get_filters(request)
        page, take = get_pagination(request)
        processed_data = FogoCruzadoService.update_occurrences(filters=filters)

        # Build response with flattened structure
        data = []
        for occurrence in processed_data:
            occurrence_dict = {
                'id': occurrence.occurrence_id,
                'lat': occurrence.latitude,
                'lng': occurrence.longitude,
                'address': occurrence.address,
                'date': occurrence.date,
                'type': occurrence.occurrence_type,
                'fatalities': occurrence.fatalities,
                'injuries': occurrence.injuries,
                'policePresent': occurrence.police_present,
                'neighborhood': occurrence.neighborhood_name,
                'city': occurrence.city_name,
                'weight': occurrence.weight,
            }
            data.append(occurrence_dict)

        # Apply pagination
        paginated_data, total = paginate(data, page, take)

        return Response({
            'data': paginated_data,
            'pagination': {
                'page': page,
                'take': take,
                'total': total,
                'pages': (total + take - 1) // take
            }
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@stats_schema
@api_view(['GET'])
def stats_view(request):
    """Return aggregated statistics for occurrences."""
    try:
        filters = get_filters(request)
        processed_data = FogoCruzadoService.update_occurrences(filters=filters)

        total_fatalities = 0
        total_injuries = 0
        police_involved = 0

        for occurrence in processed_data:
            total_fatalities += occurrence.fatalities
            total_injuries += occurrence.injuries
            if occurrence.police_present:
                police_involved += 1

        total = len(processed_data)
        police_percentage = round((police_involved / total * 100)) if total > 0 else 0

        return Response({
            'totalIncidents': total,
            'totalFatalities': total_fatalities,
            'totalInjuries': total_injuries,
            'policeInvolvedCount': police_involved,
            'policeInvolvedPercentage': police_percentage,
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@monthly_schema
@api_view(['GET'])
def monthly_view(request):
    """Return monthly breakdown of occurrences."""
    try:
        filters = get_filters(request)
        processed_data = FogoCruzadoService.update_occurrences(filters=filters)

        monthly_data = defaultdict(lambda: {'incidents': 0, 'fatalities': 0, 'injuries': 0})

        for occurrence in processed_data:
            month_key = occurrence.date.strftime('%Y-%m')
            monthly_data[month_key]['incidents'] += 1
            monthly_data[month_key]['fatalities'] += occurrence.fatalities
            monthly_data[month_key]['injuries'] += occurrence.injuries

        # Convert to sorted list
        monthly_list = [
            {'month': month, **data}
            for month, data in sorted(monthly_data.items())
        ]

        return Response({'data': monthly_list})
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@by_city_schema
@api_view(['GET'])
def by_city_view(request):
    """Return breakdown of occurrences by city."""
    try:
        filters = get_filters(request)
        processed_data = FogoCruzadoService.update_occurrences(filters=filters)

        city_data = defaultdict(lambda: {'incidents': 0, 'fatalities': 0})

        for occurrence in processed_data:
            city_name = occurrence.city_name or 'Unknown'
            city_data[city_name]['incidents'] += 1
            city_data[city_name]['fatalities'] += occurrence.fatalities

        # Convert to sorted list by incidents (descending)
        city_list = [
            {'city': city, **data}
            for city, data in sorted(city_data.items(), key=lambda x: x[1]['incidents'], reverse=True)
        ]

        return Response({'data': city_list})
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@filters_schema
@api_view(['GET'])
def filters_view(request):
    """Return available filter options for dropdowns."""
    try:
        # Fetch all data without filters to get all options
        processed_data = FogoCruzadoService.update_occurrences(filters={
            'initialdate': request.GET.get('initialdate'),
            'finaldate': request.GET.get('finaldate'),
        })

        types = set()
        cities = set()

        for occurrence in processed_data:
            if occurrence.occurrence_type:
                types.add(occurrence.occurrence_type)
            if occurrence.city_name:
                cities.add(occurrence.city_name)

        return Response({
            'types': sorted(list(types)),
            'cities': sorted(list(cities)),
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)
