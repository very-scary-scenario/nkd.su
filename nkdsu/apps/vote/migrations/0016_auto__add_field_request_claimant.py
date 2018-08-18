# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Request.claimant'
        db.add_column(u'vote_request', 'claimant',
                      self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='claims', null=True, to=orm['auth.User']),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Request.claimant'
        db.delete_column(u'vote_request', 'claimant_id')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
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
            'Meta': {'ordering': "['-created']", 'object_name': 'Request'},
            'blob': ('django.db.models.fields.TextField', [], {}),
            'claimant': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'claims'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'filled': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'filled_by': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
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
            'showtime': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'voting_allowed': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        u'vote.track': {
            'Meta': {'object_name': 'Track'},
            'added': ('django.db.models.fields.DateTimeField', [], {}),
            'background_art': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'composer': ('django.db.models.fields.CharField', [], {'max_length': '500', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '16', 'primary_key': 'True'}),
            'id3_album': ('django.db.models.fields.CharField', [], {'max_length': '500', 'blank': 'True'}),
            'id3_artist': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'id3_title': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'inudesu': ('django.db.models.fields.BooleanField', [], {}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '500', 'blank': 'True'}),
            'msec': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'revealed': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'})
        },
        u'vote.twitteruser': {
            'Meta': {'object_name': 'TwitterUser'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_abuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'screen_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {}),
            'user_id': ('django.db.models.fields.BigIntegerField', [], {'unique': 'True'})
        },
        u'vote.userbadge': {
            'Meta': {'unique_together': "[['badge', 'user']]", 'object_name': 'UserBadge'},
            'badge': ('django.db.models.fields.CharField', [], {'max_length': '12'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['vote.TwitterUser']"})
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