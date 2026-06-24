"""Isolated Fogo Cruzado HTTP client.

Talks HTTP to the provider and nothing else: no Django models, no DB, no app
imports. One client per ingestion run logs in once and reuses the token, so the
old per-request token cache is no longer needed.
"""
from __future__ import annotations

import logging
from collections.abc import Iterator

import requests

logger = logging.getLogger(__name__)

BASE = 'https://api-service.fogocruzado.org.br/api/v2'
LOGIN_URL = f'{BASE}/auth/login'
OCCURRENCES_URL = f'{BASE}/occurrences'


class FogoCruzadoError(RuntimeError):
    """A page failed mid-pagination; caller keeps what it already fetched."""


class FogoCruzadoClient:
    def __init__(self, email, password, state_id, *, per_page=1000, max_pages=50, timeout=30):
        self.email = email
        self.password = password
        self.state_id = state_id
        self.per_page = per_page
        self.max_pages = max_pages
        self.timeout = timeout
        self.session = requests.Session()
        self._token: str | None = None

    def login(self, *, force=False) -> str:
        if self._token and not force:
            return self._token
        resp = self.session.post(
            LOGIN_URL,
            json={'email': self.email, 'password': self.password},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        token = (resp.json().get('data') or {}).get('accessToken')
        if not token:
            raise FogoCruzadoError('login succeeded but no accessToken in response')
        self._token = token
        return token

    def _get_page(self, params: dict) -> dict:
        """GET one page, refreshing the token once on 401."""
        for attempt in (1, 2):
            headers = {'Authorization': f'Bearer {self.login()}'}
            resp = self.session.get(
                OCCURRENCES_URL, headers=headers, params=params, timeout=self.timeout
            )
            if resp.status_code == 401 and attempt == 1:
                self.login(force=True)
                continue
            resp.raise_for_status()
            return resp.json()
        raise FogoCruzadoError('unauthorized after token refresh')

    def iter_occurrences(self, *, initial_date=None, final_date=None) -> Iterator[list[dict]]:
        """Yield raw occurrence records page by page for the whole state.

        Raises FogoCruzadoError if a page fails, *after* earlier pages were
        yielded — the caller persists those and records a `partial` run.
        """
        base = {'idState': self.state_id}
        if initial_date:
            base['initialdate'] = initial_date
        if final_date:
            base['finaldate'] = final_date

        page = 1
        while page <= self.max_pages:
            params = {**base, 'take': self.per_page, 'page': page}
            try:
                payload = self._get_page(params)
            except requests.RequestException as exc:
                raise FogoCruzadoError(f'page {page} failed: {exc}') from exc

            data = payload.get('data') or []
            if data:
                yield data

            meta = payload.get('pageMeta') or {}
            if not meta.get('hasNextPage') or not data:
                break
            page += 1
