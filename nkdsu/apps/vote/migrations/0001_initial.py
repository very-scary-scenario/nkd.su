# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Show'
        db.create_table(u'vote_show', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('showtime', self.gf('django.db.models.fields.DateTimeField')(db_index=True)),
            ('end', self.gf('django.db.models.fields.DateTimeField')(db_index=True)),
        ))
        db.send_create_signal(u'vote', ['Show'])

        # Adding model 'TwitterUser'
        db.create_table(u'vote_twitteruser', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('screen_name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('user_id', self.gf('django.db.models.fields.BigIntegerField')(unique=True)),
            ('user_image', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('is_abuser', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')()),
        ))
        db.send_create_signal(u'vote', ['TwitterUser'])

        # Adding model 'Track'
        db.create_table(u'vote_track', (
            ('id', self.gf('django.db.models.fields.CharField')(max_length=16, primary_key=True)),
            ('id3_title', self.gf('django.db.models.fields.CharField')(max_length=500)),
            ('id3_artist', self.gf('django.db.models.fields.CharField')(max_length=500)),
            ('id3_album', self.gf('django.db.models.fields.CharField')(max_length=500, blank=True)),
            ('msec', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('added', self.gf('django.db.models.fields.DateTimeField')()),
            ('revealed', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('hidden', self.gf('django.db.models.fields.BooleanField')()),
            ('inudesu', self.gf('django.db.models.fields.BooleanField')()),
        ))
        db.send_create_signal(u'vote', ['Track'])

        # Adding model 'Vote'
        db.create_table(u'vote_vote', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('date', self.gf('django.db.models.fields.DateTimeField')(db_index=True)),
            ('text', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('twitter_user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['vote.TwitterUser'], null=True, blank=True)),
            ('tweet_id', self.gf('django.db.models.fields.BigIntegerField')(null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=40, blank=True)),
            ('kind', self.gf('django.db.models.fields.CharField')(max_length=10, blank=True)),
        ))
        db.send_create_signal(u'vote', ['Vote'])

        # Adding M2M table for field tracks on 'Vote'
        m2m_table_name = db.shorten_name(u'vote_vote_tracks')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('vote', models.ForeignKey(orm[u'vote.vote'], null=False)),
            ('track', models.ForeignKey(orm[u'vote.track'], null=False))
        ))
        db.create_unique(m2m_table_name, ['vote_id', 'track_id'])

        # Adding model 'Play'
        db.create_table(u'vote_play', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('date', self.gf('django.db.models.fields.DateTimeField')(db_index=True)),
            ('track', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['vote.Track'])),
            ('tweet_id', self.gf('django.db.models.fields.BigIntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'vote', ['Play'])

        # Adding model 'Block'
        db.create_table(u'vote_block', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('track', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['vote.Track'])),
            ('reason', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('show', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['vote.Show'])),
        ))
        db.send_create_signal(u'vote', ['Block'])

        # Adding unique constraint on 'Block', fields ['show', 'track']
        db.create_unique(u'vote_block', ['show_id', 'track_id'])

        # Adding model 'Shortlist'
        db.create_table(u'vote_shortlist', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('show', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['vote.Show'])),
            ('track', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['vote.Track'])),
            ('index', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal(u'vote', ['Shortlist'])

        # Adding unique constraint on 'Shortlist', fields ['show', 'track']
        db.create_unique(u'vote_shortlist', ['show_id', 'track_id'])

        # Adding unique constraint on 'Shortlist', fields ['show', 'index']
        db.create_unique(u'vote_shortlist', ['show_id', 'index'])

        # Adding model 'Discard'
        db.create_table(u'vote_discard', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('show', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['vote.Show'])),
            ('track', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['vote.Track'])),
        ))
        db.send_create_signal(u'vote', ['Discard'])

        # Adding unique constraint on 'Discard', fields ['show', 'track']
        db.create_unique(u'vote_discard', ['show_id', 'track_id'])

        # Adding model 'Request'
        db.create_table(u'vote_request', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('successful', self.gf('django.db.models.fields.BooleanField')()),
            ('blob', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'vote', ['Request'])

        # Adding model 'Note'
        db.create_table(u'vote_note', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('track', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['vote.Track'])),
            ('show', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['vote.Show'], null=True, blank=True)),
            ('public', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('content', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'vote', ['Note'])


    def backwards(self, orm):
        # Removing unique constraint on 'Discard', fields ['show', 'track']
        db.delete_unique(u'vote_discard', ['show_id', 'track_id'])

        # Removing unique constraint on 'Shortlist', fields ['show', 'index']
        db.delete_unique(u'vote_shortlist', ['show_id', 'index'])

        # Removing unique constraint on 'Shortlist', fields ['show', 'track']
        db.delete_unique(u'vote_shortlist', ['show_id', 'track_id'])

        # Removing unique constraint on 'Block', fields ['show', 'track']
        db.delete_unique(u'vote_block', ['show_id', 'track_id'])

        # Deleting model 'Show'
        db.delete_table(u'vote_show')

        # Deleting model 'TwitterUser'
        db.delete_table(u'vote_twitteruser')

        # Deleting model 'Track'
        db.delete_table(u'vote_track')

        # Deleting model 'Vote'
        db.delete_table(u'vote_vote')

        # Removing M2M table for field tracks on 'Vote'
        db.delete_table(db.shorten_name(u'vote_vote_tracks'))

        # Deleting model 'Play'
        db.delete_table(u'vote_play')

        # Deleting model 'Block'
        db.delete_table(u'vote_block')

        # Deleting model 'Shortlist'
        db.delete_table(u'vote_shortlist')

        # Deleting model 'Discard'
        db.delete_table(u'vote_discard')

        # Deleting model 'Request'
        db.delete_table(u'vote_request')

        # Deleting model 'Note'
        db.delete_table(u'vote_note')


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
            'showtime': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'})
        },
        u'vote.track': {
            'Meta': {'object_name': 'Track'},
            'added': ('django.db.models.fields.DateTimeField', [], {}),
            'hidden': ('django.db.models.fields.BooleanField', [], {}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '16', 'primary_key': 'True'}),
            'id3_album': ('django.db.models.fields.CharField', [], {'max_length': '500', 'blank': 'True'}),
            'id3_artist': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'id3_title': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'inudesu': ('django.db.models.fields.BooleanField', [], {}),
            'msec': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'revealed': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
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
            'text': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'tracks': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['vote.Track']", 'db_index': 'True', 'symmetrical': 'False'}),
            'tweet_id': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'twitter_user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['vote.TwitterUser']", 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['vote']