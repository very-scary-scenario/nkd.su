from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('vote', '0020_alter_track_has_hook'),
    ]

    operations = [
        migrations.AddField(
            model_name='track',
            name='archived',
            field=models.BooleanField(
                default=False,
                help_text=(
                    'This will never be played again, but cannot be removed from the database for historical reasons.'
                ),
            ),
        ),
        migrations.AlterField(
            model_name='track',
            name='hidden',
            field=models.BooleanField(
                help_text='This track has not been revealed, or is pending migration.'
            ),
        ),
    ]
