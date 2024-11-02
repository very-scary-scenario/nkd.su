from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vote', '0028_pigeon_vote_kind'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userbadge',
            name='badge',
            field=models.CharField(
                choices=[
                    ('tblc', '{name} bought Take Back Love City for the RSPCA.'),
                    (
                        'charity-2016',
                        '{name} donated to the Very Scary Scenario charity streams for Special Effect in 2016.',
                    ),
                    (
                        'charity-2017',
                        '{name} donated to the Very Scary Scenario charity streams and Neko Desu All-Nighter for Cancer Research UK in 2017.',
                    ),
                    (
                        'charity-2018',
                        '{name} donated to the Very Scary Scenario charity streams for Cancer Research UK in 2018.',
                    ),
                    (
                        'charity-2019',
                        '{name} donated to the Very Scary Scenario charity streams for Samaritans in 2019.',
                    ),
                    (
                        'charity-2020',
                        '{name} donated to the Very Scary Scenario charity streams for Cancer Research UK in 2020.',
                    ),
                    (
                        'charity-2021',
                        '{name} donated to the Very Scary Scenario charity streams for Mind in 2021.',
                    ),
                    (
                        'charity-2022',
                        '{name} donated to the Very Scary Scenario charity streams for akt in 2022.',
                    ),
                    (
                        'charity-2023',
                        '{name} donated to the Very Scary Scenario charity streams and Neko Desu All-Nighter for the National Autistic Society in 2023.',
                    ),
                    (
                        'charity-2024',
                        '{name} donated to the Very Scary Scenario charity streams for Medical Aid for Palestinians in 2024.',
                    ),
                ],
                max_length=12,
            ),
        ),
    ]
