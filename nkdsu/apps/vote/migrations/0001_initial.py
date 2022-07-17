# Generated by Django 2.2.9 on 2020-01-19 19:47

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import nkdsu.apps.vote.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Show',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('showtime', models.DateTimeField(db_index=True)),
                ('end', models.DateTimeField(db_index=True)),
                ('message', models.TextField(blank=True)),
                ('voting_allowed', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='Track',
            fields=[
                ('id', models.CharField(max_length=16, primary_key=True, serialize=False)),
                ('id3_title', models.CharField(max_length=500)),
                ('id3_artist', models.CharField(max_length=500)),
                ('id3_album', models.CharField(blank=True, max_length=500)),
                ('msec', models.IntegerField(blank=True, null=True)),
                ('added', models.DateTimeField()),
                ('composer', models.CharField(blank=True, max_length=500)),
                ('label', models.CharField(blank=True, max_length=500)),
                ('revealed', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('hidden', models.BooleanField()),
                ('inudesu', models.BooleanField()),
                ('background_art', models.ImageField(blank=True, upload_to=nkdsu.apps.vote.models.art_path)),
            ],
        ),
        migrations.CreateModel(
            name='TwitterUser',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('screen_name', models.CharField(max_length=100)),
                ('user_id', models.BigIntegerField(unique=True)),
                ('name', models.CharField(max_length=100)),
                ('is_patron', models.BooleanField(default=False)),
                ('is_abuser', models.BooleanField(default=False)),
                ('updated', models.DateTimeField()),
            ],
        ),
        migrations.CreateModel(
            name='Vote',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField(db_index=True)),
                ('text', models.TextField(blank=True)),
                ('tweet_id', models.BigIntegerField(blank=True, null=True)),
                ('name', models.CharField(blank=True, max_length=40)),
                ('kind', models.CharField(blank=True, choices=[('email', 'email'), ('text', 'text'), ('tweet', 'tweet'), ('person', 'in person'), ('phone', 'on the phone')], max_length=10)),
                ('show', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='vote_set', to='vote.Show')),
                ('tracks', models.ManyToManyField(db_index=True, to='vote.Track')),
                ('twitter_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='vote.TwitterUser')),
            ],
        ),
        migrations.CreateModel(
            name='Request',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('successful', models.BooleanField()),
                ('blob', models.TextField()),
                ('filled', models.DateTimeField(blank=True, null=True)),
                ('claimant', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='claims', to=settings.AUTH_USER_MODEL)),
                ('filled_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created'],
            },
        ),
        migrations.CreateModel(
            name='Play',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField(db_index=True)),
                ('tweet_id', models.BigIntegerField(blank=True, null=True)),
                ('show', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vote.Show')),
                ('track', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vote.Track')),
            ],
        ),
        migrations.CreateModel(
            name='Note',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('public', models.BooleanField(default=False)),
                ('content', models.TextField()),
                ('show', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='vote.Show')),
                ('track', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vote.Track')),
            ],
        ),
        migrations.CreateModel(
            name='UserBadge',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('badge', models.CharField(choices=[('tblc', '{user.name} bought Take Back Love City for the RSPCA.'), ('charity-2016', '{user.name} donated to the Very Scary Scenario charity streams for Special Effect in 2016.'), ('charity-2017', '{user.name} donated to the Very Scary Scenario charity streams and Neko Desu All-Nighter for Cancer Research UK in 2017.'), ('charity-2018', '{user.name} donated to the Very Scary Scenario charity streams for Cancer Research UK in 2018.'), ('charity-2019', '{user.name} donated to the Very Scary Scenario charity streams for Samaritans in 2019.')], max_length=12)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vote.TwitterUser')),
            ],
            options={
                'unique_together': {('badge', 'user')},
            },
        ),
        migrations.CreateModel(
            name='Shortlist',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('index', models.IntegerField(default=0)),
                ('show', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vote.Show')),
                ('track', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vote.Track')),
            ],
            options={
                'ordering': ['-show__showtime', 'index'],
                'unique_together': {('show', 'index'), ('show', 'track')},
            },
        ),
        migrations.CreateModel(
            name='Discard',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('show', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vote.Show')),
                ('track', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vote.Track')),
            ],
            options={
                'unique_together': {('show', 'track')},
            },
        ),
        migrations.CreateModel(
            name='Block',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reason', models.CharField(max_length=256)),
                ('show', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vote.Show')),
                ('track', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vote.Track')),
            ],
            options={
                'unique_together': {('show', 'track')},
            },
        ),
    ]
