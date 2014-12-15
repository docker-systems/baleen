# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Project'
        db.create_table(u'project_project', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('site_url', self.gf('django.db.models.fields.URLField')(max_length=255, null=True, blank=True)),
            ('scm_url', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('github_token', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('github_data_received', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('branch', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('manual_config', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('public_key', self.gf('django.db.models.fields.TextField')()),
            ('private_key', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'project', ['Project'])

        # Adding model 'Credential'
        db.create_table(u'project_credential', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['project.Project'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('value', self.gf('django.db.models.fields.TextField')(max_length=255)),
            ('environment', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'project', ['Credential'])


    def backwards(self, orm):
        # Deleting model 'Project'
        db.delete_table(u'project_project')

        # Deleting model 'Credential'
        db.delete_table(u'project_credential')


    models = {
        u'project.credential': {
            'Meta': {'object_name': 'Credential'},
            'environment': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['project.Project']"}),
            'value': ('django.db.models.fields.TextField', [], {'max_length': '255'})
        },
        u'project.project': {
            'Meta': {'object_name': 'Project'},
            'branch': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'github_data_received': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'github_token': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'manual_config': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'private_key': ('django.db.models.fields.TextField', [], {}),
            'public_key': ('django.db.models.fields.TextField', [], {}),
            'scm_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'site_url': ('django.db.models.fields.URLField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['project']