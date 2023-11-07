from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('vote', '0019_badges_for_normal_users'),
    ]

    operations = [
        migrations.AlterField(
            model_name='track',
            name='has_hook',
            field=models.BooleanField(
                help_text=(
                    'Whether this track has a hook in Myriad. Null if not matched'
                    ' against a Myriad export.'
                ),
                blank=True,
                null=True,
            ),
        ),
    ]
