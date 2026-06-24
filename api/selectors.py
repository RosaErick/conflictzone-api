"""Query layer: filters + SQL aggregations over indexed columns.

Keeps business/query logic out of the views. Series are bucketed in local time
(America/Sao_Paulo) so a "day" matches what the user sees, while rows stay UTC.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
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

    return qs


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
