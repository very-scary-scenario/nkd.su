# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

from ..models import Vote, Play


class Migration(SchemaMigration):

    def forwards(self, orm):

        for model in [Vote, Play]:
            for instance in model.objects.all():
                instance.save()


    def backwards(self, orm):
        pass

    complete_apps = ['vote']
