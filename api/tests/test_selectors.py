"""Selector/aggregation tests, including local-timezone bucketing."""
import uuid
from datetime import UTC, date, datetime

from django.contrib.gis.geos import Point
from django.test import TestCase

from api import selectors
from api.models import Occurrence

DT = datetime(2024, 1, 1, 12, tzinfo=UTC)


def occ(occurred_at, **kw):
    defaults = dict(
        external_id=uuid.uuid4(), address='', neighborhood='', city='Rio de Janeiro',
        main_reason='Execução', police_action=False, agent_presence=False,
        fatalities=0, injuries=0, weight=0, raw={},
    )
    defaults.update(kw)
    return Occurrence.objects.create(occurred_at=occurred_at, **defaults)


class TimeseriesTzTests(TestCase):
    def test_day_bucketing_uses_local_timezone(self):
        # 2024-01-02 01:00 UTC == 2024-01-01 22:00 in America/Sao_Paulo (-03:00).
        occ(datetime(2024, 1, 2, 1, 0, tzinfo=UTC))
        # 2024-01-02 04:00 UTC == 2024-01-02 01:00 local.
        occ(datetime(2024, 1, 2, 4, 0, tzinfo=UTC))

        rows = selectors.timeseries(Occurrence.objects.all(), 'day')
        periods = {r['period']: r['incidents'] for r in rows}
        self.assertEqual(periods, {'2024-01-01': 1, '2024-01-02': 1})


class StatsTests(TestCase):
    def test_stats_aggregate(self):
        occ(datetime(2024, 1, 1, 12, tzinfo=UTC), fatalities=2, injuries=1, police_action=True)
        occ(datetime(2024, 1, 1, 13, tzinfo=UTC), fatalities=0, injuries=3, agent_presence=True)
        occ(datetime(2024, 1, 1, 14, tzinfo=UTC))

        s = selectors.stats(Occurrence.objects.all())
        self.assertEqual(s['totalIncidents'], 3)
        self.assertEqual(s['totalFatalities'], 2)
        self.assertEqual(s['totalInjuries'], 4)
        self.assertEqual(s['policeInvolvedCount'], 2)
        self.assertEqual(s['policeInvolvedPercentage'], 67)


class FilterTests(TestCase):
    def test_date_range_is_half_open_in_local_time(self):
        # 2024-01-01 02:00 UTC == 2023-12-31 23:00 local -> outside Jan 1 filter.
        occ(datetime(2024, 1, 1, 2, 0, tzinfo=UTC), city='Out')
        # 2024-01-01 12:00 UTC == 09:00 local -> inside.
        occ(datetime(2024, 1, 1, 12, 0, tzinfo=UTC), city='In')

        qs = selectors.filtered_occurrences(
            {'initialdate': date(2024, 1, 1), 'finaldate': date(2024, 1, 1)}
        )
        cities = list(qs.values_list('city', flat=True))
        self.assertEqual(cities, ['In'])

    def test_police_present_filter(self):
        occ(datetime(2024, 1, 1, 12, tzinfo=UTC), police_action=True, city='P')
        occ(datetime(2024, 1, 1, 12, tzinfo=UTC), city='N')

        present = selectors.filtered_occurrences({'policePresent': True})
        absent = selectors.filtered_occurrences({'policePresent': False})
        self.assertEqual(list(present.values_list('city', flat=True)), ['P'])
        self.assertEqual(list(absent.values_list('city', flat=True)), ['N'])


class BreakdownTests(TestCase):
    def test_breakdown_by_city_sorted_desc(self):
        occ(datetime(2024, 1, 1, 12, tzinfo=UTC), city='A', fatalities=1)
        occ(datetime(2024, 1, 1, 12, tzinfo=UTC), city='B')
        occ(datetime(2024, 1, 1, 12, tzinfo=UTC), city='B')

        rows = selectors.breakdown(Occurrence.objects.all(), 'city')
        self.assertEqual(rows[0], {'city': 'B', 'incidents': 2, 'fatalities': 0})
        self.assertEqual(rows[1], {'city': 'A', 'incidents': 1, 'fatalities': 1})


class BboxFilterTests(TestCase):
    def test_bbox_includes_and_excludes_by_location(self):
        occ(DT, city='In', location=Point(-43.2, -22.9, srid=4326))
        occ(DT, city='Out', location=Point(-40.0, -20.0, srid=4326))

        qs = selectors.filtered_occurrences({'bbox': (-43.5, -23.0, -43.0, -22.5)})
        self.assertEqual(list(qs.values_list('city', flat=True)), ['In'])


class DensityGridTests(TestCase):
    def test_points_in_same_cell_are_grouped(self):
        # Two points within 0.01° of each other snap to the same grid node; a third
        # is far enough to land in its own cell.
        occ(DT, location=Point(-43.201, -22.901, srid=4326))
        occ(DT, location=Point(-43.202, -22.902, srid=4326))
        occ(DT, location=Point(-43.260, -22.960, srid=4326))
        occ(DT, location=None)  # null location is ignored

        fc = selectors.density_grid(Occurrence.objects.all(), 0.01)
        self.assertEqual(fc['type'], 'FeatureCollection')
        counts = sorted(f['properties']['count'] for f in fc['features'])
        self.assertEqual(counts, [1, 2])
        self.assertEqual(sum(counts), 3)

    def test_bbox_filter_applies_to_density(self):
        occ(DT, location=Point(-43.2, -22.9, srid=4326))
        occ(DT, location=Point(-40.0, -20.0, srid=4326))

        qs = selectors.filtered_occurrences({'bbox': (-43.5, -23.0, -43.0, -22.5)})
        fc = selectors.density_grid(qs, 0.01)
        self.assertEqual(sum(f['properties']['count'] for f in fc['features']), 1)
