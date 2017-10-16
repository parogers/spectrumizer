#!/usr/bin/env python3

import datetime
import django
from django.db.models import Q
from django.utils import timezone
import site
import time
import sys
import os
import collections
import argparse

import bootstrap
bootstrap.setup_django()

from scan.models import ScanSession, SnapshotInfo, ScanData

##

parser = argparse.ArgumentParser(description="Dumps spectrum scan data")
parser.add_argument("-s", dest="summary",
                    help="Show summary only", action="store_true")
parser.add_argument("scan_id")
args = parser.parse_args()

info = SnapshotInfo.objects.get(id=int(args.scan_id))

#by_date[local.year, local.month, local.day] += 1

if (args.summary):
    local = timezone.localtime(info.scan_start)
    session = info.scan_session
    print("""Session
Session:   %(scan_id)d
Start:     %(start)0.1f
End:       %(end)0.1f
Scan time: %(scan_time)s""" % {
    "scan_id" : session.id,
    "scan_time" : local.strftime("%Y-%m-%d %H:%M:%S"),
    "start" : session.freq_start/1e6,
    "end" : session.freq_stop/1e6,
})
else:
    for data in ScanData.objects.all().filter(snapshot_info_id=info.id):
        print(data.frequency, data.power)
