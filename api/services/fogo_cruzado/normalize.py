"""Pure transformation layer: raw Fogo Cruzado payload -> typed DTO.

Django-free on purpose so every transformation is unit-testable without a DB,
GDAL, or the network. The ingestion command turns these DTOs into model rows.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime

# Victim.situation values that count as human casualties.
DEAD = 'Dead'
WOUNDED = 'Wounded'
HUMAN = 'People'


@dataclass(frozen=True)
class OccurrenceDTO:
    external_id: str
    occurred_at: datetime          # tz-aware, UTC
    latitude: float | None
    longitude: float | None
    address: str
    neighborhood: str
    city: str
    main_reason: str
    police_action: bool
    agent_presence: bool
    fatalities: int
    injuries: int
    weight: float
    raw: dict


def parse_datetime(value: str) -> datetime:
    """Parse an ISO-8601 string to a tz-aware UTC datetime.

    Provider sends e.g. '2024-01-01T00:49:00.000Z'. A naive result is forbidden,
    so we always attach/normalize to UTC.
    """
    if not value:
        raise ValueError('empty datetime')
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _victim_type(victim: dict) -> str | None:
    t = victim.get('type')
    if isinstance(t, dict):
        return t.get('name')
    return t


def count_victims(victims: list | None, situation: str) -> int:
    """Count human victims (type == 'People') with the given situation.

    The old code counted every victim including animals; humans only is correct.
    """
    if not victims:
        return 0
    return sum(
        1 for v in victims
        if v.get('situation') == situation and _victim_type(v) == HUMAN
    )


def get_main_reason(item: dict) -> str:
    ctx = item.get('contextInfo') or {}
    reason = ctx.get('mainReason') or {}
    return reason.get('name') or ''


def validate_coordinate(value, is_latitude: bool = True) -> float | None:
    """Parse a coordinate string to a float in range, or None if invalid."""
    if value is None:
        return None
    try:
        cleaned = re.sub(r'[^\d.-]', '', str(value).strip())
        if re.match(r'^-?\d+(?:\.\d+)?$', cleaned) is None:
            return None
        coord = float(cleaned)
    except (ValueError, TypeError):
        return None
    limit = 90 if is_latitude else 180
    return coord if -limit <= coord <= limit else None


def calculate_weight(item: dict) -> float:
    weight = 4 + len(item.get('victims') or []) * 20
    if item.get('policeAction') and item.get('agentPresence'):
        weight += 15
    return float(weight)


def _name(obj) -> str:
    return obj.get('name', '') if isinstance(obj, dict) else ''


def normalize_occurrence(item: dict) -> OccurrenceDTO:
    """Raw provider record -> OccurrenceDTO. Raises KeyError if `id` is missing."""
    victims = item.get('victims') or []
    return OccurrenceDTO(
        external_id=item['id'],
        occurred_at=parse_datetime(item.get('date', '')),
        latitude=validate_coordinate(item.get('latitude'), is_latitude=True),
        longitude=validate_coordinate(item.get('longitude'), is_latitude=False),
        address=item.get('address') or '',
        neighborhood=_name(item.get('neighborhood')),
        city=_name(item.get('city')),
        main_reason=get_main_reason(item),
        police_action=bool(item.get('policeAction')),
        agent_presence=bool(item.get('agentPresence')),
        fatalities=count_victims(victims, DEAD),
        injuries=count_victims(victims, WOUNDED),
        weight=calculate_weight(item),
        raw=item,
    )


def _demo():
    # ponytail: one runnable check covering the non-trivial transforms.
    dt = parse_datetime('2024-01-01T00:49:00.000Z')
    assert dt.tzinfo is not None and dt.utcoffset().total_seconds() == 0, dt

    victims = [
        {'situation': 'Dead', 'type': 'People'},
        {'situation': 'Wounded', 'type': 'People'},
        {'situation': 'Dead', 'type': 'Animals'},          # not a human casualty
        {'situation': 'Wounded', 'type': {'name': 'People'}},  # nested type form
    ]
    assert count_victims(victims, DEAD) == 1, count_victims(victims, DEAD)
    assert count_victims(victims, WOUNDED) == 2, count_victims(victims, WOUNDED)

    assert validate_coordinate('-22.89') == -22.89
    assert validate_coordinate('999') is None       # out of lat range
    assert validate_coordinate('abc') is None

    item = {
        'id': 'abc', 'date': '2024-01-01T00:49:00.000Z',
        'latitude': '-22.89', 'longitude': '-43.25',
        'address': 'Jacare', 'neighborhood': {'name': 'JACARE'},
        'city': {'name': 'Rio de Janeiro'},
        'contextInfo': {'mainReason': {'name': 'Execução'}},
        'policeAction': True, 'agentPresence': True, 'victims': victims,
    }
    dto = normalize_occurrence(item)
    assert dto.main_reason == 'Execução'
    assert dto.city == 'Rio de Janeiro'
    assert dto.fatalities == 1 and dto.injuries == 2
    assert dto.weight == 4 + 4 * 20 + 15, dto.weight
    print('normalize._demo OK')


if __name__ == '__main__':
    _demo()
