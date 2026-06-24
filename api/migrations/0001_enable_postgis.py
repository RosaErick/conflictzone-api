from django.contrib.postgres.operations import CreateExtension
from django.db import migrations


class Migration(migrations.Migration):
    """Enable PostGIS before any geometry column is created."""

    initial = True

    dependencies = []

    operations = [
        CreateExtension('postgis'),
    ]
