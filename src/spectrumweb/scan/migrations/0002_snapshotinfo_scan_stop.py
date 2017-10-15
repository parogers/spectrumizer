# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scan', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='snapshotinfo',
            name='scan_stop',
            field=models.DateTimeField(default=None, verbose_name='scan stop'),
        ),
    ]
