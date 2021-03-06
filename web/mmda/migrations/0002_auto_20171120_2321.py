# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-11-21 04:21
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mmda', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DataAggregate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('time_created', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='FileMetadata',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file_name', models.CharField(max_length=200)),
                ('storage_path', models.CharField(max_length=500)),
                ('creator_name', models.CharField(max_length=200)),
                ('time_created', models.DateTimeField()),
                ('last_modified', models.DateTimeField()),
                ('document_type_id', models.PositiveIntegerField()),
            ],
        ),
        migrations.RemoveField(
            model_name='choice',
            name='question',
        ),
        migrations.DeleteModel(
            name='Choice',
        ),
        migrations.DeleteModel(
            name='Question',
        ),
    ]
