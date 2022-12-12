# Generated by Django 3.2.12 on 2022-04-23 17:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vote', '0005_auto_20210508_1518'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='twitteruser',
            options={'ordering': ['screen_name']},
        ),
        migrations.AlterField(
            model_name='track',
            name='id3_artist',
            field=models.CharField(max_length=1000),
        ),
        migrations.AlterField(
            model_name='userbadge',
            name='badge',
            field=models.CharField(
                choices=[
                    ('tblc', '{user.name} bought Take Back Love City for the RSPCA.'),
                    (
                        'charity-2016',
                        '{user.name} donated to the Very Scary Scenario charity streams for Special Effect in 2016.',
                    ),
                    (
                        'charity-2017',
                        '{user.name} donated to the Very Scary Scenario charity streams and Neko Desu All-Nighter for Cancer Research UK in 2017.',
                    ),
                    (
                        'charity-2018',
                        '{user.name} donated to the Very Scary Scenario charity streams for Cancer Research UK in 2018.',
                    ),
                    (
                        'charity-2019',
                        '{user.name} donated to the Very Scary Scenario charity streams for Samaritans in 2019.',
                    ),
                    (
                        'charity-2020',
                        '{user.name} donated to the Very Scary Scenario charity streams in 2020.',
                    ),
                    (
                        'charity-2021',
                        '{user.name} donated to the Very Scary Scenario charity streams in 2021.',
                    ),
                ],
                max_length=12,
            ),
        ),
    ]
