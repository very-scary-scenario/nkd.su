import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import nkdsu.apps.vote.models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('vote', '0024_proroulettecommitment'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserTrackList',
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
                ('name', models.CharField(max_length=100)),
                ('public', models.BooleanField(default=False)),
            ],
            bases=(nkdsu.apps.vote.models.CleanOnSaveMixin, models.Model),
        ),
        migrations.CreateModel(
            name='UserTrackListTrack',
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
                ('index', models.PositiveIntegerField()),
                (
                    'track',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to='vote.track'
                    ),
                ),
                (
                    'track_list',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to='vote.usertracklist',
                    ),
                ),
            ],
            bases=(nkdsu.apps.vote.models.CleanOnSaveMixin, models.Model),
        ),
        migrations.AddField(
            model_name='usertracklist',
            name='tracks',
            field=models.ManyToManyField(
                through='vote.UserTrackListTrack', to='vote.track'
            ),
        ),
        migrations.AddField(
            model_name='usertracklist',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='track_lists',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddConstraint(
            model_name='usertracklisttrack',
            constraint=models.UniqueConstraint(
                models.F('track_list'),
                models.F('index'),
                name='user_track_list_track_index_unique',
                violation_error_message='each index must only appear once per list',
            ),
        ),
        migrations.AddConstraint(
            model_name='usertracklisttrack',
            constraint=models.UniqueConstraint(
                models.F('track_list'),
                models.F('track'),
                name='user_track_list_track_track_unique',
                violation_error_message='tracks can only be present once per list',
            ),
        ),
        migrations.AddConstraint(
            model_name='usertracklist',
            constraint=models.UniqueConstraint(
                models.F('user'),
                models.F('name'),
                name='user_track_list_name_unique',
                violation_error_message='list names must be unique',
            ),
        ),
    ]
