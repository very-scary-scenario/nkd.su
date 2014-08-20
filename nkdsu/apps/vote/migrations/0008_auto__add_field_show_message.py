# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Show.message'
        db.add_column(u'vote_show', 'message',
                      self.gf('django.db.models.fields.TextField')(default='', blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Show.message'
        db.delete_column(u'vote_show', 'message')


    models = {
        u'vote.block': {
            'Meta': {'unique_together': "[['show', 'track']]", 'object_name': 'Block'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'reason': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'show': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['vote.Show']"}),
            'track': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['vote.Track']"})
        },
        u'vote.discard': {
            'Meta': {'unique_together': "[['show', 'track']]", 'object_name': 'Discard'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'show': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['vote.Show']"}),
            'track': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['vote.Track']"})
        },
        u'vote.note': {
            'Meta': {'object_name': 'Note'},
            'content': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'show': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['vote.Show']", 'null': 'True', 'blank': 'True'}),
            'track': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['vote.Track']"})
        },
        u'vote.play': {
            'Meta': {'object_name': 'Play'},
            'date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'show': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['vote.Show']"}),
            'track': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['vote.Track']"}),
            'tweet_id': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'vote.request': {
            'Meta': {'object_name': 'Request'},
            'blob': ('django.db.models.fields.TextField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'successful': ('django.db.models.fields.BooleanField', [], {})
        },
        u'vote.shortlist': {
            'Meta': {'ordering': "['-show__showtime', 'index']", 'unique_together': "[['show', 'track'], ['show', 'index']]", 'object_name': 'Shortlist'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'show': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['vote.Show']"}),
            'track': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['vote.Track']"})
        },
        u'vote.show': {
            'Meta': {'object_name': 'Show'},
            'end': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'showtime': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'})
        },
        u'vote.track': {
            'Meta': {'object_name': 'Track'},
            'added': ('django.db.models.fields.DateTimeField', [], {}),
            'background_art': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '16', 'primary_key': 'True'}),
            'id3_album': ('django.db.models.fields.CharField', [], {'max_length': '500', 'blank': 'True'}),
            'id3_artist': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'id3_title': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'inudesu': ('django.db.models.fields.BooleanField', [], {}),
            'msec': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'revealed': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'})
        },
        u'vote.twitteruser': {
            'Meta': {'object_name': 'TwitterUser'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_abuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'screen_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {}),
            'user_id': ('django.db.models.fields.BigIntegerField', [], {'unique': 'True'}),
            'user_image': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        u'vote.vote': {
            'Meta': {'object_name': 'Vote'},
            'date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '10', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'show': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'vote_set'", 'to': u"orm['vote.Show']"}),
            'text': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'tracks': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['vote.Track']", 'db_index': 'True', 'symmetrical': 'False'}),
            'tweet_id': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'twitter_user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['vote.TwitterUser']", 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['vote']