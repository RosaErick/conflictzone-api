"""Testes de transformação pura — sem DB, sem GDAL, sem rede (SimpleTestCase)."""
from django.test import SimpleTestCase

from api.services.fogo_cruzado import normalize as N
from api.tests.factories import make_item


class ParseDatetimeTests(SimpleTestCase):
    def test_z_suffix_becomes_utc_aware(self):
        dt = N.parse_datetime('2024-01-01T00:49:00.000Z')
        self.assertIsNotNone(dt.tzinfo)
        self.assertEqual(dt.utcoffset().total_seconds(), 0)

    def test_offset_is_normalized_to_utc(self):
        dt = N.parse_datetime('2024-01-01T00:00:00-03:00')
        self.assertEqual(dt.hour, 3)  # 00:00 -03:00 == 03:00 UTC

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            N.parse_datetime('')


class VictimCountTests(SimpleTestCase):
    def setUp(self):
        self.victims = [
            {'situation': 'Dead', 'type': 'People'},
            {'situation': 'Wounded', 'type': 'People'},
            {'situation': 'Dead', 'type': 'Animals'},          # excluído
            {'situation': 'Wounded', 'type': {'name': 'People'}},  # forma aninhada
        ]

    def test_counts_humans_only(self):
        self.assertEqual(N.count_victims(self.victims, N.DEAD), 1)
        self.assertEqual(N.count_victims(self.victims, N.WOUNDED), 2)

    def test_empty(self):
        self.assertEqual(N.count_victims(None, N.DEAD), 0)


class CoordinateTests(SimpleTestCase):
    def test_valid(self):
        self.assertEqual(N.validate_coordinate('-22.89'), -22.89)

    def test_out_of_range(self):
        self.assertIsNone(N.validate_coordinate('999', is_latitude=True))

    def test_garbage(self):
        self.assertIsNone(N.validate_coordinate('abc'))
        self.assertIsNone(N.validate_coordinate(None))


class NormalizeOccurrenceTests(SimpleTestCase):
    def test_full_record(self):
        item = make_item(
            policeAction=True, agentPresence=True,
            victims=[{'situation': 'Dead', 'type': 'People'}],
        )
        dto = N.normalize_occurrence(item)
        self.assertEqual(dto.main_reason, 'Execução')
        self.assertEqual(dto.city, 'Rio de Janeiro')
        self.assertEqual(dto.fatalities, 1)
        self.assertEqual(dto.weight, 4 + 1 * 20 + 15)
        self.assertIs(dto.raw, item)

    def test_missing_id_raises(self):
        item = make_item()
        del item['id']
        with self.assertRaises(KeyError):
            N.normalize_occurrence(item)
