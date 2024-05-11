from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('vote', '0025_user_track_list'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usertracklist',
            name='slug',
            field=models.SlugField(max_length=100),
        ),
    ]
