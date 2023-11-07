import django.db.models.deletion
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
                    ('tblc', '{name} bought Take Back Love City for the RSPCA.'),
                    (
                        'charity-2016',
                        (
                            '{name} donated to the Very Scary Scenario charity streams'
                            ' for Special Effect in 2016.'
                        ),
                    ),
                    (
                        'charity-2017',
                        (
                            '{name} donated to the Very Scary Scenario charity streams'
                            ' and Neko Desu All-Nighter for Cancer Research UK in 2017.'
                        ),
                    ),
                    (
                        'charity-2018',
                        (
                            '{name} donated to the Very Scary Scenario charity streams'
                            ' for Cancer Research UK in 2018.'
                        ),
                    ),
                    (
                        'charity-2019',
                        (
                            '{name} donated to the Very Scary Scenario charity streams'
                            ' for Samaritans in 2019.'
                        ),
                    ),
                    (
                        'charity-2020',
                        (
                            '{name} donated to the Very Scary Scenario charity streams'
                            ' for Cancer Research UK in 2020.'
                        ),
                    ),
                    (
                        'charity-2021',
                        (
                            '{name} donated to the Very Scary Scenario charity streams'
                            ' for Mind in 2021.'
                        ),
                    ),
                    (
                        'charity-2022',
                        (
                            '{name} donated to the Very Scary Scenario charity streams'
                            ' for akt in 2022.'
                        ),
                    ),
                    (
                        'charity-2023',
                        (
                            '{name} donated to the Very Scary Scenario charity streams'
                            ' and Neko Desu All-Nighter for the National Autistic'
                            ' Society in 2023.'
                        ),
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
            name='profile',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to='vote.profile',
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
                    models.Q(
                        ('profile__isnull', True), ('twitter_user__isnull', False)
                    ),
                    models.Q(
                        ('profile__isnull', False), ('twitter_user__isnull', True)
                    ),
                    _connector='OR',
                ),
                name='badge_must_have_user',
                violation_error_message=(
                    'Badges must be associated with either a profile or twitter user'
                ),
            ),
        ),
    ]
