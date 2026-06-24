from django.contrib.gis.db import models as gis_models
from django.db import models


class Occurrence(models.Model):
    """Uma ocorrência ingerida da Fogo Cruzado.

    Colunas tipadas e explícitas guiam toda query; `raw` guarda o payload original
    para auditoria/reprocesso. `external_id` é o UUID do provedor e a chave de dedup.
    """

    external_id = models.UUIDField(unique=True)
    occurred_at = models.DateTimeField(db_index=True)
    # geography=True -> distância em metros; PointField cria o índice GiST sozinho.
    location = gis_models.PointField(geography=True, srid=4326, null=True, blank=True)
    address = models.TextField(blank=True, default='')
    neighborhood = models.CharField(max_length=255, blank=True, default='')
    city = models.CharField(max_length=255, blank=True, default='')
    main_reason = models.CharField(max_length=255, blank=True, default='')
    police_action = models.BooleanField(default=False)
    agent_presence = models.BooleanField(default=False)
    # ponytail: contagens derivadas de vítimas humanas (type=='People') cobrem os
    # dashboards atuais; criar tabela Victim normalizada no 1º filtro por vítima.
    fatalities = models.PositiveIntegerField(default=0)
    injuries = models.PositiveIntegerField(default=0)
    weight = models.FloatField(default=0)
    raw = models.JSONField(default=dict)
    ingested_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Occurrence'
        verbose_name_plural = 'Occurrences'
        indexes = [
            models.Index(fields=['city']),
            models.Index(fields=['main_reason']),
            models.Index(fields=['neighborhood']),
        ]

    @property
    def police_present(self):
        return self.police_action or self.agent_presence

    def __str__(self):
        return f'{self.address or self.external_id} on {self.occurred_at:%Y-%m-%d}'


class IngestionRun(models.Model):
    """Registro de auditoria de uma execução da ingestão — nada de falha silenciosa."""

    SUCCESS = 'success'
    PARTIAL = 'partial'
    FAILED = 'failed'
    STATUS_CHOICES = [(SUCCESS, SUCCESS), (PARTIAL, PARTIAL), (FAILED, FAILED)]

    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=FAILED)
    fetched = models.PositiveIntegerField(default=0)
    created = models.PositiveIntegerField(default=0)
    updated = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f'IngestionRun {self.pk} {self.status} ({self.started_at:%Y-%m-%d %H:%M})'
