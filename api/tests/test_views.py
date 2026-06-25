"""Testes de contrato dos endpoints: validação (400), defasagem (503), caminho feliz (200)."""
import uuid
from datetime import UTC, datetime, timedelta

from django.contrib.gis.geos import Point
from django.test import TestCase
from django.utils import timezone as djtz

from api.models import IngestionRun, Occurrence


def make_run(age_hours=0.0, status=IngestionRun.SUCCESS):
    run = IngestionRun.objects.create(status=status, fetched=1)
    run.finished_at = djtz.now() - timedelta(hours=age_hours)
    run.save()
    return run


def make_occ(**kw):
    defaults = dict(
        external_id=uuid.uuid4(),
        occurred_at=datetime(2024, 1, 1, 12, tzinfo=UTC),
        address='A', neighborhood='N', city='Rio de Janeiro', main_reason='Execução',
        fatalities=1, injuries=0, weight=24, raw={},
    )
    defaults.update(kw)
    return Occurrence.objects.create(**defaults)


class ValidationTests(TestCase):
    def setUp(self):
        make_run()
        make_occ()

    def test_bad_date_is_400(self):
        self.assertEqual(self.client.get('/occurrences/?initialdate=nope').status_code, 400)

    def test_inverted_range_is_400(self):
        r = self.client.get('/occurrences/stats/?initialdate=2024-02-01&finaldate=2024-01-01')
        self.assertEqual(r.status_code, 400)

    def test_take_over_max_is_400(self):
        self.assertEqual(self.client.get('/occurrences/?take=99999').status_code, 400)

    def test_bad_granularity_is_400(self):
        r = self.client.get('/occurrences/timeseries/?granularity=hour')
        self.assertEqual(r.status_code, 400)


class StalenessTests(TestCase):
    def test_no_ingestion_is_503(self):
        make_occ()  # há dado, mas o pipeline nunca rodou com sucesso
        self.assertEqual(self.client.get('/occurrences/').status_code, 503)

    def test_stale_ingestion_is_503(self):
        make_run(age_hours=99)
        make_occ()
        self.assertEqual(self.client.get('/occurrences/stats/').status_code, 503)

    def test_fresh_ingestion_is_200(self):
        make_run(age_hours=0)
        make_occ()
        self.assertEqual(self.client.get('/occurrences/').status_code, 200)


class ContractTests(TestCase):
    def setUp(self):
        make_run()
        make_occ()

    def test_occurrences_shape(self):
        body = self.client.get('/occurrences/').json()
        self.assertIn('data', body)
        self.assertIn('pagination', body)
        row = body['data'][0]
        self.assertEqual(
            set(row),
            {'id', 'lat', 'lng', 'address', 'date', 'type', 'fatalities',
             'injuries', 'policePresent', 'neighborhood', 'city', 'weight'},
        )

    def test_health_reports_ingestion_age(self):
        body = self.client.get('/health/').json()
        self.assertEqual(body['status'], 'ok')
        self.assertIsNotNone(body['lastIngestion'])
        self.assertIn('ageHours', body['lastIngestion'])


class DensityTests(TestCase):
    def test_density_returns_featurecollection(self):
        make_run()
        make_occ(location=Point(-43.2, -22.9, srid=4326))
        body = self.client.get('/occurrences/density/').json()
        self.assertEqual(body['type'], 'FeatureCollection')
        self.assertEqual(body['features'][0]['properties']['count'], 1)

    def test_invalid_bbox_is_400(self):
        make_run()
        make_occ(location=Point(-43.2, -22.9, srid=4326))
        self.assertEqual(self.client.get('/occurrences/density/?bbox=1,2,3').status_code, 400)

    def test_out_of_range_cell_is_400(self):
        make_run()
        self.assertEqual(self.client.get('/occurrences/density/?cell=1').status_code, 400)

    def test_density_no_ingestion_is_503(self):
        make_occ(location=Point(-43.2, -22.9, srid=4326))
        self.assertEqual(self.client.get('/occurrences/density/').status_code, 503)


class ByNeighborhoodTests(TestCase):
    def test_breakdown_by_neighborhood_sorted_desc(self):
        make_run()
        make_occ(neighborhood='Centro')
        make_occ(neighborhood='Centro')
        make_occ(neighborhood='Bangu')
        body = self.client.get('/occurrences/by-neighborhood/').json()
        self.assertEqual(
            body['data'][0], {'neighborhood': 'Centro', 'incidents': 2, 'fatalities': 2}
        )
        rows = {r['neighborhood']: r['incidents'] for r in body['data']}
        self.assertEqual(rows, {'Centro': 2, 'Bangu': 1})
