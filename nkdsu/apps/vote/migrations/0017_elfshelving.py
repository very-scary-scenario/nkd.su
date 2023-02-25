from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import nkdsu.apps.vote.models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('vote', '0016_authenticated_requests'),
    ]

    operations = [
        migrations.CreateModel(
            name='ElfShelving',
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
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('reason_created', models.TextField(blank=True)),
                ('disabled_at', models.DateTimeField(blank=True, null=True)),
                ('reason_disabled', models.TextField(blank=True)),
                (
                    'created_by',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='created_shelvings',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'disabled_by',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='disabled_shelvings',
                        to=settings.AUTH_USER_MODEL,
                        null=True,
                    ),
                ),
                (
                    'request',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='shelvings',
                        to='vote.request',
                    ),
                ),
            ],
            bases=(nkdsu.apps.vote.models.CleanOnSaveMixin, models.Model),
        ),
    ]
