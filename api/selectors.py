"""Query layer: filters + SQL aggregations over indexed columns.

Keeps business/query logic out of the views. Series are bucketed in local time
(America/Sao_Paulo) so a "day" matches what the user sees, while rows stay UTC.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.gis.geos import Polygon
from django.db import connection
from django.db.models import Count, Q, QuerySet, Sum
from django.db.models.functions import TruncDay, TruncMonth, TruncWeek

from api.models import Occurrence

LOCAL_TZ = ZoneInfo(settings.LOCAL_TZ)

_TRUNC = {'day': TruncDay, 'week': TruncWeek, 'month': TruncMonth}


def filtered_occurrences(filters: dict) -> QuerySet:
    """Apply validated filters to the Occurrence queryset (all in SQL)."""
    qs = Occurrence.objects.all()

    # Date bounds: convert local calendar dates to a precise UTC half-open range
    # [start, end) so boundary rows near midnight land on the right side.
    if filters.get('initialdate'):
        start = datetime.combine(filters['initialdate'], time.min, tzinfo=LOCAL_TZ)
        qs = qs.filter(occurred_at__gte=start)
    if filters.get('finaldate'):
        end = datetime.combine(filters['finaldate'] + timedelta(days=1), time.min, tzinfo=LOCAL_TZ)
        qs = qs.filter(occurred_at__lt=end)

    if filters.get('type'):
        qs = qs.filter(main_reason__in=filters['type'])
    if filters.get('mainReason'):
        qs = qs.filter(main_reason=filters['mainReason'])
    if filters.get('city'):
        qs = qs.filter(city__iexact=filters['city'])

    police = filters.get('policePresent')
    if police is not None:
        present = Q(police_action=True) | Q(agent_presence=True)
        qs = qs.filter(present) if police else qs.exclude(present)

    status = filters.get('victimStatus')
    if status == 'fatalities':
        qs = qs.filter(fatalities__gt=0)
    elif status == 'injuries':
        qs = qs.filter(injuries__gt=0)
    elif status == 'none':
        qs = qs.filter(fatalities=0, injuries=0)

    if filters.get('bbox'):
        # bbox is (minLng, minLat, maxLng, maxLat) — the order from_bbox expects.
        poly = Polygon.from_bbox(filters['bbox'])
        poly.srid = 4326
        qs = qs.filter(location__intersects=poly)  # hits the GiST index on location

    return qs


def density_grid(qs: QuerySet, cell: float) -> dict:
    """Aggregate occurrences into a square grid and return a GeoJSON FeatureCollection.

    Snaps each point to a grid of side ``cell`` (degrees) with PostGIS
    ``ST_SnapToGrid`` and counts per cell. Output is one center point per cell
    with ``properties.count`` — ready for a MapLibre heatmap weight.

    Reuses the WHERE of ``filtered_occurrences`` by compiling the incoming
    queryset, so every filter (incl. bbox) applies for free.

    ponytail: square grid via ``ST_SnapToGrid`` (PostGIS core — no extra
    extension). Upgrade to H3 or vector tiles (``ST_AsMVT``) when the square grid
    bothers or the dataset grows much. `location` is geography, so we cast to
    geometry (``::geometry``) — ``ST_SnapToGrid`` only accepts geometry. Raw but
    fully parameterized: never interpolate user values into SQL.
    """
    located = qs.filter(location__isnull=False).values('location')
    inner_sql, inner_params = located.query.sql_with_params()
    sql = (
        'SELECT ST_X(c) AS gx, ST_Y(c) AS gy, count(*) AS n '
        'FROM (SELECT ST_SnapToGrid(location::geometry, %s) AS c '
        f'FROM ({inner_sql}) sub) g '
        'GROUP BY c'
    )
    with connection.cursor() as cur:
        cur.execute(sql, (cell, *inner_params))
        rows = cur.fetchall()

    half = cell / 2  # ST_SnapToGrid returns the cell origin; offset to its center.
    return {
        'type': 'FeatureCollection',
        'features': [
            {
                'type': 'Feature',
                'geometry': {'type': 'Point', 'coordinates': [gx + half, gy + half]},
                'properties': {'count': n},
            }
            for gx, gy, n in rows
        ],
    }


def stats(qs: QuerySet) -> dict:
    agg = qs.aggregate(
        total=Count('id'),
        fatalities=Sum('fatalities'),
        injuries=Sum('injuries'),
        police=Count('id', filter=Q(police_action=True) | Q(agent_presence=True)),
    )
    total = agg['total'] or 0
    police = agg['police'] or 0
    return {
        'totalIncidents': total,
        'totalFatalities': agg['fatalities'] or 0,
        'totalInjuries': agg['injuries'] or 0,
        'policeInvolvedCount': police,
        'policeInvolvedPercentage': round(police / total * 100) if total else 0,
    }


def timeseries(qs: QuerySet, granularity: str) -> list[dict]:
    """Incidents/fatalities/injuries bucketed by day|week|month in local tz."""
    trunc = _TRUNC[granularity]
    rows = (
        qs.annotate(period=trunc('occurred_at', tzinfo=LOCAL_TZ))
        .values('period')
        .annotate(
            incidents=Count('id'),
            fatalities=Sum('fatalities'),
            injuries=Sum('injuries'),
        )
        .order_by('period')
    )
    return [
        {
            'period': r['period'].astimezone(LOCAL_TZ).date().isoformat(),
            'incidents': r['incidents'],
            'fatalities': r['fatalities'] or 0,
            'injuries': r['injuries'] or 0,
        }
        for r in rows
    ]


def breakdown(qs: QuerySet, field: str) -> list[dict]:
    """Incidents + fatalities grouped by a column (e.g. city, neighborhood)."""
    rows = (
        qs.values(field)
        .annotate(incidents=Count('id'), fatalities=Sum('fatalities'))
        .order_by('-incidents')
    )
    return [
        {
            field: r[field] or 'Unknown',
            'incidents': r['incidents'],
            'fatalities': r['fatalities'] or 0,
        }
        for r in rows
    ]


def filter_options(qs: QuerySet) -> dict:
    types = qs.exclude(main_reason='').values_list('main_reason', flat=True).distinct()
    cities = qs.exclude(city='').values_list('city', flat=True).distinct()
    return {'types': sorted(types), 'cities': sorted(cities)}
