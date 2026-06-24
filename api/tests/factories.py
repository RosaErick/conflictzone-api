"""Shared helpers for tests: build raw provider records without the network."""


def make_item(external_id='11111111-1111-1111-1111-111111111111', **overrides):
    item = {
        'id': external_id,
        'date': '2024-01-01T12:00:00.000Z',
        'latitude': '-22.9',
        'longitude': '-43.2',
        'address': 'Somewhere',
        'neighborhood': {'name': 'CENTRO'},
        'city': {'name': 'Rio de Janeiro'},
        'contextInfo': {'mainReason': {'name': 'Execução'}},
        'policeAction': False,
        'agentPresence': False,
        'victims': [],
    }
    item.update(overrides)
    return item
