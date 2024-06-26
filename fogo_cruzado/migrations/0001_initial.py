# Generated by Django 5.0.1 on 2024-01-10 19:57

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Occurrence',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('occurrence_id', models.CharField(max_length=255, unique=True)),
                ('latitude', models.FloatField()),
                ('longitude', models.FloatField()),
                ('address', models.TextField()),
                ('date', models.DateTimeField()),
                ('police_action', models.BooleanField()),
                ('agent_presence', models.BooleanField()),
            ],
            options={
                'verbose_name': 'Occurrence',
                'verbose_name_plural': 'Occurrences',
            },
        ),
    ]
