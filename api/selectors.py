"""Camada de consulta: filtros + agregações SQL sobre colunas indexadas.

Tira a lógica de query das views. As séries são agrupadas em horário local
(America/Sao_Paulo) para o "dia" bater com o do usuário; as linhas ficam em UTC.
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
    """Aplica os filtros validados ao queryset de Occurrence (tudo em SQL)."""
    qs = Occurrence.objects.all()

    # Datas: converte o dia local num intervalo UTC semiaberto [início, fim) para
    # ocorrências perto da meia-noite caírem no lado certo.
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
        # bbox = (minLng, minLat, maxLng, maxLat) — ordem que from_bbox espera.
        poly = Polygon.from_bbox(filters['bbox'])
        poly.srid = 4326
        qs = qs.filter(location__intersects=poly)  # usa o índice GiST em location

    return qs


def density_grid(qs: QuerySet, cell: float) -> dict:
    """Agrega ocorrências num grid quadrado → GeoJSON FeatureCollection.

    Snapa cada ponto a um grid de lado ``cell`` (graus) com ``ST_SnapToGrid`` e
    conta por célula; cada feature é o centro da célula com ``properties.count``
    (peso pronto p/ heatmap do MapLibre). Reusa o WHERE de ``filtered_occurrences``
    compilando o queryset. `location` é geography → cast p/ geometry. SQL cru,
    100% parametrizado (nunca interpolar valor de usuário).

    ponytail: grid quadrado (PostGIS nativo); troque por H3/vector tiles se crescer.
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

    half = cell / 2  # ST_SnapToGrid devolve a origem da célula; desloca p/ o centro.
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
    """Incidentes/mortos/feridos agrupados por dia|semana|mês no fuso local."""
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
    """Incidentes + mortos agrupados por uma coluna (ex.: city, neighborhood)."""
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
