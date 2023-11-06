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
        migrations.AddConstraint(
            model_name='userwebsite',
            constraint=models.UniqueConstraint(
                fields=('url', 'profile'),
                name='unique_url_per_profile',
                violation_error_message="You can't provide the same URL more than once",
            ),
        ),
    ]
