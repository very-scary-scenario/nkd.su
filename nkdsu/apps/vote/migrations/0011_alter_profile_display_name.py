# Generated by Django 3.2.16 on 2022-12-12 13:04

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('vote', '0010_profile'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='display_name',
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
