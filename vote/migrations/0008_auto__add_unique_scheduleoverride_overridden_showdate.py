# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding unique constraint on 'ScheduleOverride', fields ['overridden_showdate']
        db.create_unique('vote_scheduleoverride', ['overridden_showdate'])


    def backwards(self, orm):
        # Removing unique constraint on 'ScheduleOverride', fields ['overridden_showdate']
        db.delete_unique('vote_scheduleoverride', ['overridden_showdate'])


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
        'vote.scheduleoverride': {
            'Meta': {'object_name': 'ScheduleOverride'},
            'finish': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'overridden_showdate': ('django.db.models.fields.DateField', [], {'unique': 'True'}),
            'start': ('django.db.models.fields.DateTimeField', [], {})
        },
        'vote.shortlist': {
            'Meta': {'object_name': 'Shortlist'},
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'track': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['vote.Track']"})
        },
        'vote.track': {
            'Meta': {'object_name': 'Track'},
            'added': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '16', 'primary_key': 'True'}),
            'id3_album': ('django.db.models.fields.CharField', [], {'max_length': '500', 'blank': 'True'}),
            'id3_artist': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'id3_title': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'msec': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
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
            'track': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['vote.Track']", 'null': 'True', 'blank': 'True'}),
            'tracks': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'multi+'", 'blank': 'True', 'to': "orm['vote.Track']"}),
            'tweet_id': ('django.db.models.fields.IntegerField', [], {'primary_key': 'True'}),
            'user_id': ('django.db.models.fields.IntegerField', [], {}),
            'user_image': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['vote']