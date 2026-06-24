from django.contrib import admin

from .models import IngestionRun, Occurrence


@admin.register(Occurrence)
class OccurrenceAdmin(admin.ModelAdmin):
    list_display = ('external_id', 'occurred_at', 'city', 'neighborhood', 'main_reason',
                    'fatalities', 'injuries')
    list_filter = ('city', 'main_reason', 'police_action', 'agent_presence')
    search_fields = ('external_id', 'address', 'neighborhood', 'city')
    date_hierarchy = 'occurred_at'


@admin.register(IngestionRun)
class IngestionRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'started_at', 'finished_at', 'fetched', 'created', 'updated')
    list_filter = ('status',)
    readonly_fields = ('started_at',)
