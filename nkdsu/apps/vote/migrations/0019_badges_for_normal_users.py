import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('vote', '0018_basic_myriad_playout_csv_export'),
    ]

    operations = [
        migrations.RenameField(
            model_name='userbadge',
            old_name='user',
            new_name='twitter_user',
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
                        '{user.name} donated to the Very Scary Scenario charity streams for Cancer Research UK in 2020.',
                    ),
                    (
                        'charity-2021',
                        '{user.name} donated to the Very Scary Scenario charity streams for Mind in 2021.',
                    ),
                    (
                        'charity-2022',
                        '{user.name} donated to the Very Scary Scenario charity streams for akt in 2022.',
                    ),
                    (
                        'charity-2023',
                        '{user.name} donated to the Very Scary Scenario charity streams and Neko Desu All-Nighter for the National Autistic Society in 2023.',
                    ),
                ],
                max_length=12,
            ),
        ),
        migrations.AlterUniqueTogether(
            name='userbadge',
            unique_together=set(),
        ),
        migrations.AddField(
            model_name='userbadge',
            name='user',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='userbadge',
            name='twitter_user',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to='vote.twitteruser',
            ),
        ),
        migrations.AddConstraint(
            model_name='userbadge',
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(('twitter_user__isnull', False), ('user__isnull', True)),
                    models.Q(('twitter_user__isnull', True), ('user__isnull', False)),
                    _connector='OR',
                ),
                name='badge_must_have_user',
            ),
        ),
    ]
