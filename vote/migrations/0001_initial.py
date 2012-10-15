# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Track'
        db.create_table('vote_track', (
            ('id', self.gf('django.db.models.fields.CharField')(max_length=16, primary_key=True)),
            ('id3_title', self.gf('django.db.models.fields.CharField')(max_length=500)),
            ('title_en', self.gf('django.db.models.fields.CharField')(max_length=500, blank=True)),
            ('title_ro', self.gf('django.db.models.fields.CharField')(max_length=500, blank=True)),
            ('title_ka', self.gf('django.db.models.fields.CharField')(max_length=500, blank=True)),
            ('id3_artist', self.gf('django.db.models.fields.CharField')(max_length=500)),
            ('id3_album', self.gf('django.db.models.fields.CharField')(max_length=500, blank=True)),
            ('show_en', self.gf('django.db.models.fields.CharField')(max_length=500, blank=True)),
            ('show_ro', self.gf('django.db.models.fields.CharField')(max_length=500, blank=True)),
            ('show_ka', self.gf('django.db.models.fields.CharField')(max_length=500, blank=True)),
            ('role', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
        ))
        db.send_create_signal('vote', ['Track'])

        # Adding model 'Vote'
        db.create_table('vote_vote', (
            ('screen_name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('text', self.gf('django.db.models.fields.CharField')(max_length=140)),
            ('user_id', self.gf('django.db.models.fields.IntegerField')()),
            ('tweet_id', self.gf('django.db.models.fields.IntegerField')(primary_key=True)),
            ('track', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['vote.Track'], blank=True)),
            ('date', self.gf('django.db.models.fields.DateTimeField')()),
            ('user_image', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=20)),
        ))
        db.send_create_signal('vote', ['Vote'])

        # Adding model 'Play'
        db.create_table('vote_play', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('datetime', self.gf('django.db.models.fields.DateTimeField')()),
            ('track', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['vote.Track'])),
            ('tweet_id', self.gf('django.db.models.fields.IntegerField')(blank=True)),
        ))
        db.send_create_signal('vote', ['Play'])

        # Adding model 'Block'
        db.create_table('vote_block', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('track', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['vote.Track'])),
            ('reason', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('vote', ['Block'])

        # Adding model 'Shortlist'
        db.create_table('vote_shortlist', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('track', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['vote.Track'])),
        ))
        db.send_create_signal('vote', ['Shortlist'])

        # Adding model 'Discard'
        db.create_table('vote_discard', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('track', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['vote.Track'])),
        ))
        db.send_create_signal('vote', ['Discard'])

        # Adding model 'ManualVote'
        db.create_table('vote_manualvote', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('track', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['vote.Track'])),
            ('kind', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('message', self.gf('django.db.models.fields.CharField')(max_length=256, blank=True)),
            ('anonymous', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('vote', ['ManualVote'])


    def backwards(self, orm):
        # Deleting model 'Track'
        db.delete_table('vote_track')

        # Deleting model 'Vote'
        db.delete_table('vote_vote')

        # Deleting model 'Play'
        db.delete_table('vote_play')

        # Deleting model 'Block'
        db.delete_table('vote_block')

        # Deleting model 'Shortlist'
        db.delete_table('vote_shortlist')

        # Deleting model 'Discard'
        db.delete_table('vote_discard')

        # Deleting model 'ManualVote'
        db.delete_table('vote_manualvote')


    models = {
        'vote.block': {
            'Meta': {'object_name': 'Block'},
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'reason': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'track': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['vote.Track']"})
        },
        'vote.discard': {
            'Meta': {'object_name': 'Discard'},
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'track': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['vote.Track']"})
        },
        'vote.manualvote': {
            'Meta': {'object_name': 'ManualVote'},
            'anonymous': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'message': ('django.db.models.fields.CharField', [], {'max_length': '256', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'track': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['vote.Track']"})
        },
        'vote.play': {
            'Meta': {'object_name': 'Play'},
            'datetime': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'track': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['vote.Track']"}),
            'tweet_id': ('django.db.models.fields.IntegerField', [], {'blank': 'True'})
        },
        'vote.shortlist': {
            'Meta': {'object_name': 'Shortlist'},
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'track': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['vote.Track']"})
        },
        'vote.track': {
            'Meta': {'object_name': 'Track'},
            'id': ('django.db.models.fields.CharField', [], {'max_length': '16', 'primary_key': 'True'}),
            'id3_album': ('django.db.models.fields.CharField', [], {'max_length': '500', 'blank': 'True'}),
            'id3_artist': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'id3_title': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'show_en': ('django.db.models.fields.CharField', [], {'max_length': '500', 'blank': 'True'}),
            'show_ka': ('django.db.models.fields.CharField', [], {'max_length': '500', 'blank': 'True'}),
            'show_ro': ('django.db.models.fields.CharField', [], {'max_length': '500', 'blank': 'True'}),
            'title_en': ('django.db.models.fields.CharField', [], {'max_length': '500', 'blank': 'True'}),
            'title_ka': ('django.db.models.fields.CharField', [], {'max_length': '500', 'blank': 'True'}),
            'title_ro': ('django.db.models.fields.CharField', [], {'max_length': '500', 'blank': 'True'})
        },
        'vote.vote': {
            'Meta': {'object_name': 'Vote'},
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'screen_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'text': ('django.db.models.fields.CharField', [], {'max_length': '140'}),
            'track': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['vote.Track']", 'blank': 'True'}),
            'tweet_id': ('django.db.models.fields.IntegerField', [], {'primary_key': 'True'}),
            'user_id': ('django.db.models.fields.IntegerField', [], {}),
            'user_image': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['vote']