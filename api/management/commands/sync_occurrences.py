from datetime import date, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from api.models import IngestionRun
from api.services.ingest import run_sync


class Command(BaseCommand):
    help = (
        'Fetch occurrences from Fogo Cruzado and upsert them into the database.\n'
        'No dates -> incremental sync of the last few days (for the hourly cron).\n'
        'Explicit --initial-date/--final-date -> backfill a fixed window.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--initial-date', dest='initial_date', default=None,
            help='YYYY-MM-DD lower bound. Omit for incremental (last N days).',
        )
        parser.add_argument(
            '--final-date', dest='final_date', default=None,
            help='YYYY-MM-DD upper bound (default: open-ended to now).',
        )
        parser.add_argument(
            '--days', type=int, default=None,
            help='Incremental window size in days when --initial-date is omitted '
                 '(default: settings.INGESTION_DEFAULT_DAYS).',
        )

    def handle(self, *args, **options):
        initial_date = options['initial_date']
        final_date = options['final_date']

        # Incremental by default: no explicit start -> only the last few days.
        # ponytail: a fixed recent window beats tracking a sync cursor at this
        # volume; the upsert is idempotent so re-fetching the overlap is harmless.
        if initial_date is None:
            days = options['days']
            if days is None:
                days = settings.INGESTION_DEFAULT_DAYS
            initial_date = (date.today() - timedelta(days=days)).isoformat()

        run = run_sync(initial_date=initial_date, final_date=final_date)
        self.stdout.write(
            f'run {run.id}: {run.status} window={initial_date}..{final_date or "now"} '
            f'fetched={run.fetched} created={run.created} updated={run.updated}'
        )
        if run.status == IngestionRun.FAILED:
            raise CommandError(run.error or 'ingestion failed')
