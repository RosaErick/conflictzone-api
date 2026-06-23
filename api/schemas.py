from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes


# Common query parameters for all occurrence endpoints
COMMON_PARAMETERS = [
    OpenApiParameter(
        name='initialdate',
        type=OpenApiTypes.DATE,
        location=OpenApiParameter.QUERY,
        description='Start date for filtering (format: YYYY-MM-DD)',
        required=False,
    ),
    OpenApiParameter(
        name='finaldate',
        type=OpenApiTypes.DATE,
        location=OpenApiParameter.QUERY,
        description='End date for filtering (format: YYYY-MM-DD)',
        required=False,
    ),
    OpenApiParameter(
        name='type',
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description='Filter by occurrence type (mainReason.name)',
        required=False,
    ),
    OpenApiParameter(
        name='city',
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description='Filter by city name',
        required=False,
    ),
    OpenApiParameter(
        name='policePresent',
        type=OpenApiTypes.BOOL,
        location=OpenApiParameter.QUERY,
        description='Filter by police presence (true/false)',
        required=False,
    ),
    OpenApiParameter(
        name='victimStatus',
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description='Filter by victim status: "fatalities", "injuries", "none", "all"',
        enum=['fatalities', 'injuries', 'none', 'all'],
        required=False,
    ),
]

PAGINATION_PARAMETERS = [
    OpenApiParameter(
        name='page',
        type=OpenApiTypes.INT,
        location=OpenApiParameter.QUERY,
        description='Page number (default: 1)',
        required=False,
    ),
    OpenApiParameter(
        name='take',
        type=OpenApiTypes.INT,
        location=OpenApiParameter.QUERY,
        description='Items per page (default: 100, max: 1000)',
        required=False,
    ),
]


# Response examples
OCCURRENCE_RESPONSE_EXAMPLE = {
    'data': [
        {
            'id': '9f229472-8748-4688-8247-416fe391aa22',
            'lat': -22.8923272,
            'lng': -43.2581953,
            'address': 'Jacare, Rio de Janeiro - RJ, Brasil',
            'date': '2024-01-01T00:49:00Z',
            'type': 'Execução',
            'fatalities': 1,
            'injuries': 0,
            'policePresent': True,
            'neighborhood': 'JACARE',
            'city': 'Rio de Janeiro',
            'weight': 24
        }
    ],
    'pagination': {
        'page': 1,
        'take': 100,
        'total': 3328,
        'pages': 34
    }
}


STATS_RESPONSE_EXAMPLE = {
    'totalIncidents': 3328,
    'totalFatalities': 465,
    'totalInjuries': 1189,
    'policeInvolvedCount': 1398,
    'policeInvolvedPercentage': 42
}


MONTHLY_RESPONSE_EXAMPLE = {
    'data': [
        {'month': '2024-01', 'incidents': 245, 'fatalities': 32, 'injuries': 89},
        {'month': '2024-02', 'incidents': 198, 'fatalities': 28, 'injuries': 72},
        {'month': '2024-03', 'incidents': 210, 'fatalities': 35, 'injuries': 95},
    ]
}


BY_CITY_RESPONSE_EXAMPLE = {
    'data': [
        {'city': 'Rio de Janeiro', 'incidents': 1842, 'fatalities': 245},
        {'city': 'Recife', 'incidents': 876, 'fatalities': 134},
        {'city': 'Salvador', 'incidents': 610, 'fatalities': 86},
    ]
}


FILTERS_RESPONSE_EXAMPLE = {
    'types': ['Execução', 'Homicidio/Tentativa', 'Ação policial', 'Operação policial', 'Disputa'],
    'cities': ['Rio de Janeiro', 'Recife', 'Salvador']
}


# Schema decorators
occurrences_schema = extend_schema(
    summary='List occurrences',
    description='''
Retrieve a paginated list of conflict/violence occurrences.

**Response fields (flattened):**
- `id`: Unique identifier
- `lat`, `lng`: Coordinates
- `address`: Location address
- `date`: ISO datetime
- `type`: Occurrence type (from contextInfo.mainReason.name)
- `fatalities`: Number of dead victims
- `injuries`: Number of injured victims
- `policePresent`: Boolean (policeAction OR agentPresence)
- `neighborhood`: Neighborhood name (flattened)
- `city`: City name (flattened)
- `weight`: Severity score
    ''',
    parameters=COMMON_PARAMETERS + PAGINATION_PARAMETERS,
    responses={
        200: {
            'type': 'object',
            'properties': {
                'data': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'string'},
                            'lat': {'type': 'number'},
                            'lng': {'type': 'number'},
                            'address': {'type': 'string'},
                            'date': {'type': 'string', 'format': 'date-time'},
                            'type': {'type': 'string'},
                            'fatalities': {'type': 'integer'},
                            'injuries': {'type': 'integer'},
                            'policePresent': {'type': 'boolean'},
                            'neighborhood': {'type': 'string'},
                            'city': {'type': 'string'},
                            'weight': {'type': 'number'},
                        }
                    }
                },
                'pagination': {
                    'type': 'object',
                    'properties': {
                        'page': {'type': 'integer'},
                        'take': {'type': 'integer'},
                        'total': {'type': 'integer'},
                        'pages': {'type': 'integer'},
                    }
                }
            }
        },
        500: {'type': 'object', 'properties': {'error': {'type': 'string'}}}
    },
    examples=[OpenApiExample('Success', value=OCCURRENCE_RESPONSE_EXAMPLE, response_only=True)],
    tags=['Occurrences']
)


stats_schema = extend_schema(
    summary='Get occurrence statistics',
    description='''
Returns aggregated statistics for occurrences matching the filter criteria.

**Response:**
- `totalIncidents`: Total number of occurrences
- `totalFatalities`: Total number of fatalities
- `totalInjuries`: Total number of injuries
- `policeInvolvedCount`: Occurrences with police presence
- `policeInvolvedPercentage`: Percentage of occurrences with police
    ''',
    parameters=COMMON_PARAMETERS,
    responses={
        200: {
            'type': 'object',
            'properties': {
                'totalIncidents': {'type': 'integer'},
                'totalFatalities': {'type': 'integer'},
                'totalInjuries': {'type': 'integer'},
                'policeInvolvedCount': {'type': 'integer'},
                'policeInvolvedPercentage': {'type': 'integer'},
            }
        },
        500: {'type': 'object', 'properties': {'error': {'type': 'string'}}}
    },
    examples=[OpenApiExample('Success', value=STATS_RESPONSE_EXAMPLE, response_only=True)],
    tags=['Statistics']
)


monthly_schema = extend_schema(
    summary='Get monthly breakdown',
    description='''
Returns a monthly breakdown of occurrences for trend charts.

**Response:** Array of monthly data with:
- `month`: Month in YYYY-MM format
- `incidents`: Number of occurrences
- `fatalities`: Number of fatalities
- `injuries`: Number of injuries
    ''',
    parameters=COMMON_PARAMETERS,
    responses={
        200: {
            'type': 'object',
            'properties': {
                'data': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'month': {'type': 'string'},
                            'incidents': {'type': 'integer'},
                            'fatalities': {'type': 'integer'},
                            'injuries': {'type': 'integer'},
                        }
                    }
                }
            }
        },
        500: {'type': 'object', 'properties': {'error': {'type': 'string'}}}
    },
    examples=[OpenApiExample('Success', value=MONTHLY_RESPONSE_EXAMPLE, response_only=True)],
    tags=['Statistics']
)


by_city_schema = extend_schema(
    summary='Get breakdown by city',
    description='''
Returns a breakdown of occurrences by city for region charts.

**Response:** Array sorted by incidents (descending) with:
- `city`: City name
- `incidents`: Number of occurrences
- `fatalities`: Number of fatalities
    ''',
    parameters=COMMON_PARAMETERS,
    responses={
        200: {
            'type': 'object',
            'properties': {
                'data': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'city': {'type': 'string'},
                            'incidents': {'type': 'integer'},
                            'fatalities': {'type': 'integer'},
                        }
                    }
                }
            }
        },
        500: {'type': 'object', 'properties': {'error': {'type': 'string'}}}
    },
    examples=[OpenApiExample('Success', value=BY_CITY_RESPONSE_EXAMPLE, response_only=True)],
    tags=['Statistics']
)


filters_schema = extend_schema(
    summary='Get available filter options',
    description='''
Returns available filter options for dynamic dropdowns.

**Response:**
- `types`: List of available occurrence types
- `cities`: List of available cities
    ''',
    parameters=[
        OpenApiParameter(
            name='initialdate',
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            description='Optional: limit types/cities to date range',
            required=False,
        ),
        OpenApiParameter(
            name='finaldate',
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            description='Optional: limit types/cities to date range',
            required=False,
        ),
    ],
    responses={
        200: {
            'type': 'object',
            'properties': {
                'types': {'type': 'array', 'items': {'type': 'string'}},
                'cities': {'type': 'array', 'items': {'type': 'string'}},
            }
        },
        500: {'type': 'object', 'properties': {'error': {'type': 'string'}}}
    },
    examples=[OpenApiExample('Success', value=FILTERS_RESPONSE_EXAMPLE, response_only=True)],
    tags=['Filters']
)


health_schema = extend_schema(
    summary='Health check',
    description='Simple health check endpoint to verify the API is running.',
    responses={200: {'type': 'string', 'example': 'Health Check! Ok!'}},
    tags=['Health']
)


fogo_cruzado_health_schema = extend_schema(
    summary='Fogo Cruzado API health check',
    description='''
Check if the Fogo Cruzado external API is available and operational.

Use this endpoint to show a notification to users when the data source is unavailable.

**Response statuses:**
- `online`: API is working correctly
- `offline`: API is unreachable (timeout or connection error)
- `error`: API returned an error status code
    ''',
    responses={
        200: {
            'type': 'object',
            'properties': {
                'status': {'type': 'string', 'enum': ['online']},
                'message': {'type': 'string'},
                'statusCode': {'type': 'integer'},
            },
            'example': {
                'status': 'online',
                'message': 'Fogo Cruzado API is operational',
                'statusCode': 200
            }
        },
        503: {
            'type': 'object',
            'properties': {
                'status': {'type': 'string', 'enum': ['offline', 'error']},
                'message': {'type': 'string'},
                'statusCode': {'type': 'integer', 'nullable': True},
            },
            'example': {
                'status': 'offline',
                'message': 'Fogo Cruzado API request timed out',
                'statusCode': None
            }
        }
    },
    tags=['Health']
)
