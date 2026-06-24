from django.contrib.postgres.operations import CreateExtension
from django.db import migrations


class Migration(migrations.Migration):
    """Habilita o PostGIS antes de criar qualquer coluna geométrica."""

    initial = True

    dependencies = []

    operations = [
        CreateExtension('postgis'),
    ]
