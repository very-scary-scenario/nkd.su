from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('vote', '0017_elfshelving'),
    ]

    operations = [
        migrations.AddField(
            model_name='track',
            name='has_hook',
            field=models.NullBooleanField(
                help_text=(
                    'Whether this track has a hook in Myriad. Null if not matched'
                    ' against a Myriad export.'
                )
            ),
        ),
        migrations.AddField(
            model_name='track',
            name='media_id',
            field=models.IntegerField(blank=True, null=True, unique=True),
        ),
    ]
