# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-11-28 23:03
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('mmda', '0005_auto_20171128_1753'),
    ]

    operations = [
        migrations.AlterField(
            model_name='category',
            name='parent_category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='mmda.Category'),
        ),
    ]
