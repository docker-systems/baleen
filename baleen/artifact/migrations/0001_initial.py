# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'ActionOutput'
        db.create_table(u'artifact_actionoutput', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('action_result', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['project.ActionResult'])),
            ('output_type', self.gf('django.db.models.fields.CharField')(default='SO', max_length=2)),
            ('output', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('data', self.gf('jsonfield.fields.JSONField')()),
        ))
        db.send_create_signal(u'artifact', ['ActionOutput'])


    def backwards(self, orm):
        # Deleting model 'ActionOutput'
        db.delete_table(u'artifact_actionoutput')


    models = {
        u'artifact.actionoutput': {
            'Meta': {'object_name': 'ActionOutput'},
            'action_result': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['project.ActionResult']"}),
            'data': ('jsonfield.fields.JSONField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'output': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'output_type': ('django.db.models.fields.CharField', [], {'default': "'SO'", 'max_length': '2'})
        },
        u'project.actionresult': {
            'Meta': {'object_name': 'ActionResult'},
            'action': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'action_slug': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'finished_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.IntegerField', [], {}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'started_at': ('django.db.models.fields.DateTimeField', [], {}),
            'status_code': ('django.db.models.fields.IntegerField', [], {'null': 'True'})
        }
    }

    complete_apps = ['artifact']