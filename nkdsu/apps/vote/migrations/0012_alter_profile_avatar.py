# Generated by Django 3.2.16 on 2022-12-12 13:23

from django.db import migrations, models
import nkdsu.apps.vote.models


class Migration(migrations.Migration):

    dependencies = [
        ('vote', '0011_alter_profile_display_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='avatar',
            field=models.ImageField(blank=True, upload_to=nkdsu.apps.vote.models.avatar_upload_path),
        ),
    ]
