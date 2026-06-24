from datetime import date, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from api.models import IngestionRun
from api.services.ingest import run_sync


class Command(BaseCommand):
    help = (
        'Busca ocorrências da Fogo Cruzado e faz upsert no banco.\n'
        'Sem datas -> sync incremental dos últimos dias (para o cron de hora em hora).\n'
        '--initial-date/--final-date -> backfill de uma janela fixa.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--initial-date', dest='initial_date', default=None,
            help='Limite inferior YYYY-MM-DD. Omita para incremental (últimos N dias).',
        )
        parser.add_argument(
            '--final-date', dest='final_date', default=None,
            help='Limite superior YYYY-MM-DD (padrão: aberto até agora).',
        )
        parser.add_argument(
            '--days', type=int, default=None,
            help='Tamanho da janela incremental em dias quando --initial-date é omitido '
                 '(padrão: settings.INGESTION_DEFAULT_DAYS).',
        )

    def handle(self, *args, **options):
        initial_date = options['initial_date']
        final_date = options['final_date']

        # Incremental por padrão: sem início explícito -> só os últimos dias.
        # ponytail: janela fixa recente bate guardar cursor de sync neste volume;
        # o upsert é idempotente, então re-buscar a sobreposição é inofensivo.
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
