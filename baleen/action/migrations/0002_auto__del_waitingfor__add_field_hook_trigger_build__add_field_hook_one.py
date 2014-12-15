# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'WaitingFor'
        db.delete_table(u'action_waitingfor')

        # Adding field 'Hook.trigger_build'
        db.add_column(u'action_hook', 'trigger_build',
                      self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='triggered_by', null=True, to=orm['project.Project']),
                      keep_default=False)

        # Adding field 'Hook.one_off'
        db.add_column(u'action_hook', 'one_off',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


        # Changing field 'Hook.post_url'
        db.alter_column(u'action_hook', 'post_url', self.gf('django.db.models.fields.URLField')(max_length=200, null=True))

        # Changing field 'Hook.email_user'
        db.alter_column(u'action_hook', 'email_user_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True))

        # Changing field 'Hook.email_address'
        db.alter_column(u'action_hook', 'email_address', self.gf('django.db.models.fields.EmailField')(max_length=255, null=True))

    def backwards(self, orm):
        # Adding model 'WaitingFor'
        db.create_table(u'action_waitingfor', (
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['project.Project'])),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('waiting_for', self.gf('django.db.models.fields.related.ForeignKey')(related_name='blocking_projects', to=orm['action.BuildDefinition'])),
        ))
        db.send_create_signal(u'action', ['WaitingFor'])

        # Deleting field 'Hook.trigger_build'
        db.delete_column(u'action_hook', 'trigger_build_id')

        # Deleting field 'Hook.one_off'
        db.delete_column(u'action_hook', 'one_off')


        # User chose to not deal with backwards NULL issues for 'Hook.post_url'
        raise RuntimeError("Cannot reverse this migration. 'Hook.post_url' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'Hook.post_url'
        db.alter_column(u'action_hook', 'post_url', self.gf('django.db.models.fields.URLField')(max_length=200))

        # User chose to not deal with backwards NULL issues for 'Hook.email_user'
        raise RuntimeError("Cannot reverse this migration. 'Hook.email_user' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'Hook.email_user'
        db.alter_column(u'action_hook', 'email_user_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User']))

        # User chose to not deal with backwards NULL issues for 'Hook.email_address'
        raise RuntimeError("Cannot reverse this migration. 'Hook.email_address' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'Hook.email_address'
        db.alter_column(u'action_hook', 'email_address', self.gf('django.db.models.fields.EmailField')(max_length=255))

    models = {
        u'action.actionresult': {
            'Meta': {'object_name': 'ActionResult'},
            'action': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'finished_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['job.Job']"}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'started_at': ('django.db.models.fields.DateTimeField', [], {}),
            'status_code': ('django.db.models.fields.IntegerField', [], {'null': 'True'})
        },
        u'action.builddefinition': {
            'Meta': {'object_name': 'BuildDefinition'},
            'commit': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'plan_type': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['project.Project']"}),
            'raw_plan': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        u'action.hook': {
            'Meta': {'object_name': 'Hook'},
            'email_address': ('django.db.models.fields.EmailField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email_author': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'email_user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'one_off': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'post_url': ('django.db.models.fields.URLField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['project.Project']"}),
            'trigger_build': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'triggered_by'", 'null': 'True', 'to': u"orm['project.Project']"}),
            'watch_for': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
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
        u'job.job': {
            'Meta': {'object_name': 'Job'},
            'commit': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'finished_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'github_data': ('jsonfield.fields.JSONField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'manual_by': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['project.Project']"}),
            'received_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'rejected': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'started_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'success': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'worker_pid': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'project.project': {
            'Meta': {'object_name': 'Project'},
            'branch': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True'}),
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

    complete_apps = ['action']