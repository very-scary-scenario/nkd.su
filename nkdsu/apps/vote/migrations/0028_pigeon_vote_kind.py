from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('vote', '0027_profile_pronouns'),
    ]

    operations = [
        migrations.AlterField(
            model_name='vote',
            name='kind',
            field=models.CharField(
                blank=True,
                choices=[
                    ('email', 'email'),
                    ('discord', 'discord'),
                    ('text', 'text'),
                    ('tweet', 'tweet'),
                    ('person', 'in person'),
                    ('pigeon', 'carrier pigeon'),
                    ('phone', 'on the phone'),
                ],
                max_length=10,
            ),
        ),
    ]
