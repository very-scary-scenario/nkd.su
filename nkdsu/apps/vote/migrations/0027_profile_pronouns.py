from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('vote', '0026_allow_long_tracklist_slugs'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='pronouns',
            field=models.CharField(blank=True, max_length=20),
        ),
    ]
