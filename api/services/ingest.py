"""Ingestion orchestration: fetch -> normalize -> idempotent upsert -> audit.

The only place that bridges the isolated client/normalizer to Django models.
Every run is recorded in IngestionRun; a mid-pagination failure keeps the data
already written and is marked `partial`, never silent.
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.contrib.gis.geos import Point
from django.utils import timezone

from api.models import IngestionRun, Occurrence

from .fogo_cruzado import FogoCruzadoClient, normalize_occurrence
from .fogo_cruzado.client import FogoCruzadoError
from .fogo_cruzado.normalize import OccurrenceDTO

logger = logging.getLogger(__name__)


def _to_point(dto: OccurrenceDTO) -> Point | None:
    if dto.latitude is None or dto.longitude is None:
        return None
    # Point takes (x=lng, y=lat).
    return Point(dto.longitude, dto.latitude, srid=4326)


def upsert_occurrence(dto: OccurrenceDTO) -> bool:
    """Idempotent upsert keyed on external_id. Returns True if newly created."""
    _, created = Occurrence.objects.update_or_create(
        external_id=dto.external_id,
        defaults={
            'occurred_at': dto.occurred_at,
            'location': _to_point(dto),
            'address': dto.address,
            'neighborhood': dto.neighborhood,
            'city': dto.city,
            'main_reason': dto.main_reason,
            'police_action': dto.police_action,
            'agent_presence': dto.agent_presence,
            'fatalities': dto.fatalities,
            'injuries': dto.injuries,
            'weight': dto.weight,
            'raw': dto.raw,
        },
    )
    return created


def build_client() -> FogoCruzadoClient:
    return FogoCruzadoClient(
        email=settings.FOGO_CRUZADO_EMAIL,
        password=settings.FOGO_CRUZADO_PASSWORD,
        state_id=settings.FOGO_CRUZADO_STATE_ID,
    )


def run_sync(*, initial_date=None, final_date=None, client=None) -> IngestionRun:
    run = IngestionRun.objects.create(status=IngestionRun.FAILED)
    client = client or build_client()
    fetched = created = updated = 0
    status = IngestionRun.SUCCESS
    error = ''
    try:
        for page in client.iter_occurrences(initial_date=initial_date, final_date=final_date):
            for item in page:
                try:
                    dto = normalize_occurrence(item)
                except (KeyError, ValueError) as exc:
                    logger.warning('skipping malformed record: %s', exc)
                    continue
                fetched += 1
                if upsert_occurrence(dto):
                    created += 1
                else:
                    updated += 1
    except FogoCruzadoError as exc:
        # Got some pages then a page failed -> partial; nothing at all -> failed.
        status = IngestionRun.PARTIAL if fetched else IngestionRun.FAILED
        error = str(exc)
        logger.error('ingestion %s: %s', status, exc)
    except Exception as exc:  # noqa: BLE001 - record any failure, never swallow it
        status = IngestionRun.FAILED
        error = str(exc)
        logger.exception('ingestion failed')
    finally:
        run.status = status
        run.fetched = fetched
        run.created = created
        run.updated = updated
        run.error = error
        run.finished_at = timezone.now()
        run.save()
    logger.info(
        'ingestion %s: fetched=%s created=%s updated=%s', status, fetched, created, updated
    )
    return run
