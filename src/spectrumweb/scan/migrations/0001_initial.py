# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ScanData',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('frequency', models.IntegerField(verbose_name='frequency')),
                ('power', models.FloatField(verbose_name='power')),
            ],
        ),
        migrations.CreateModel(
            name='ScanSession',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('freq_start', models.IntegerField(verbose_name='starting frequency')),
                ('freq_stop', models.IntegerField(verbose_name='stopping frequency')),
                ('keywords', models.CharField(max_length=255, verbose_name='keywords')),
                ('notes', models.TextField(verbose_name='notes')),
                ('capture_device', models.CharField(default='', max_length=64)),
                ('capture_tuner', models.CharField(default='', max_length=64)),
                ('gain', models.FloatField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='SnapshotInfo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('scan_start', models.DateTimeField(verbose_name='scan start')),
                ('scan_session', models.ForeignKey(to='scan.ScanSession')),
            ],
        ),
        migrations.AddField(
            model_name='scandata',
            name='snapshot_info',
            field=models.ForeignKey(to='scan.SnapshotInfo'),
        ),
    ]
