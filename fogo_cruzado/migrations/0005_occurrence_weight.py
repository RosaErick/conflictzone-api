# Generated by Django 5.0.1 on 2024-01-15 21:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fogo_cruzado', '0004_alter_occurrence_context_info_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='occurrence',
            name='weight',
            field=models.FloatField(blank=True, null=True),
        ),
    ]
