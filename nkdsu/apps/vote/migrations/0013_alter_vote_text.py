# Generated by Django 3.2.16 on 2022-12-16 15:47

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('vote', '0012_alter_profile_avatar'),
    ]

    operations = [
        migrations.AlterField(
            model_name='vote',
            name='text',
            field=models.TextField(
                blank=True,
                help_text='A comment to be shown alongside your request',
                max_length=280,
            ),
        ),
    ]
