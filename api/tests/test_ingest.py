"""Testes de ingestão: upsert idempotente + run auditado, sem rede (fake client)."""
from django.test import TestCase

from api.models import IngestionRun, Occurrence
from api.services.fogo_cruzado import normalize_occurrence
from api.services.fogo_cruzado.client import FogoCruzadoError
from api.services.ingest import run_sync, upsert_occurrence
from api.tests.factories import make_item


class FakeClient:
    def __init__(self, pages):
        self.pages = pages

    def iter_occurrences(self, *, initial_date=None, final_date=None):
        yield from self.pages


class FailingClient:
    """Gera uma página e falha — simula um 502 do upstream no meio da paginação."""

    def __init__(self, page):
        self.page = page

    def iter_occurrences(self, *, initial_date=None, final_date=None):
        yield self.page
        raise FogoCruzadoError('page 2 failed')


class UpsertTests(TestCase):
    def test_upsert_is_idempotent(self):
        dto = normalize_occurrence(make_item())
        self.assertTrue(upsert_occurrence(dto))   # criou
        self.assertFalse(upsert_occurrence(dto))  # atualizou, não duplicou
        self.assertEqual(Occurrence.objects.count(), 1)

    def test_upsert_refreshes_fields(self):
        upsert_occurrence(normalize_occurrence(make_item(address='Old')))
        upsert_occurrence(normalize_occurrence(make_item(address='New')))
        self.assertEqual(Occurrence.objects.get().address, 'New')


class RunSyncTests(TestCase):
    def test_success_run_records_counts(self):
        pages = [[make_item('a' * 8 + '-1111-1111-1111-111111111111')],
                 [make_item('b' * 8 + '-1111-1111-1111-111111111111')]]
        run = run_sync(client=FakeClient(pages))
        self.assertEqual(run.status, IngestionRun.SUCCESS)
        self.assertEqual(run.fetched, 2)
        self.assertEqual(run.created, 2)
        self.assertIsNotNone(run.finished_at)
        self.assertEqual(Occurrence.objects.count(), 2)

    def test_partial_keeps_fetched_data(self):
        page = [make_item('c' * 8 + '-1111-1111-1111-111111111111')]
        run = run_sync(client=FailingClient(page))
        self.assertEqual(run.status, IngestionRun.PARTIAL)
        self.assertEqual(run.created, 1)
        self.assertTrue(run.error)
        self.assertEqual(Occurrence.objects.count(), 1)  # não descartado

    def test_malformed_record_is_skipped_not_fatal(self):
        good = make_item('d' * 8 + '-1111-1111-1111-111111111111')
        bad = make_item('e' * 8 + '-1111-1111-1111-111111111111')
        del bad['id']  # KeyError no normalize -> pulado
        run = run_sync(client=FakeClient([[bad, good]]))
        self.assertEqual(run.status, IngestionRun.SUCCESS)
        self.assertEqual(run.fetched, 1)
        self.assertEqual(Occurrence.objects.count(), 1)
