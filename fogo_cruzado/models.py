from django.db import models

class Occurrence(models.Model):
    occurrence_id = models.CharField(max_length=255, unique=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    address = models.TextField()
    date = models.DateTimeField()
    police_action = models.BooleanField()
    agent_presence = models.BooleanField()
    
    def __str__(self):
        return f"{self.address} on {self.date.strftime('%Y-%m-%d')}"

    class Meta:
        verbose_name = "Occurrence"
        verbose_name_plural = "Occurrences"
