# Generated by Django 4.2.7 on 2023-11-06 10:33

from django.db import migrations, models
import django.db.models.deletion
import nkdsu.apps.vote.models


class Migration(migrations.Migration):
    dependencies = [
        ('vote', '0021_track_archival'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserWebsite',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('url', models.URLField()),
                (
                    'profile',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='websites',
                        to='vote.profile',
                    ),
                ),
            ],
            bases=(nkdsu.apps.vote.models.CleanOnSaveMixin, models.Model),
        ),
    ]
