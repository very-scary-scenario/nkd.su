from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('vote', '0022_userwebsite'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='show',
            constraint=models.UniqueConstraint(
                models.F('showtime__date'), name='unique_showtime_dates'
            ),
        ),
    ]
