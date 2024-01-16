import json
from django.db import models
from django.core.serializers.json import DjangoJSONEncoder

class Occurrence(models.Model):
    occurrence_id = models.CharField(max_length=255, unique=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    address = models.TextField()
    date = models.DateTimeField()
    police_action = models.BooleanField()
    agent_presence = models.BooleanField()
    context_info = models.TextField(blank=True, null=True)
    victims = models.TextField(blank=True, null=True)
    weight = models.FloatField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if isinstance(self.context_info, dict):
            self.context_info = json.dumps(self.context_info, cls=DjangoJSONEncoder)
        if isinstance(self.victims, list):
            self.victims = json.dumps(self.victims, cls=DjangoJSONEncoder)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.address} on {self.date.strftime('%Y-%m-%d')}"
    class Meta:
        verbose_name = "Occurrence"
        verbose_name_plural = "Occurrences"
