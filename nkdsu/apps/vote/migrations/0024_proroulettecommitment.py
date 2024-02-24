from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import nkdsu.apps.vote.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('vote', '0023_show_unique_showtime_dates'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProRouletteCommitment',
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
                (
                    'show',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, to='vote.show'
                    ),
                ),
                (
                    'track',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to='vote.track'
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            bases=(nkdsu.apps.vote.models.CleanOnSaveMixin, models.Model),
        ),
        migrations.AddConstraint(
            model_name='proroulettecommitment',
            constraint=models.UniqueConstraint(
                models.F('show'),
                models.F('user'),
                name='pro_roulette_commitment_unique',
                violation_error_message='a user can only have one pro roulette commitment per show',
            ),
        ),
    ]
