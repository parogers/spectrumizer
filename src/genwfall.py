#!/usr/bin/env python

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
from PIL import Image

from rtlpower import rtlpower

# Change into the program directory (so we know where our django code is at)
path = os.path.dirname(sys.argv[0])
if (path):
    os.chdir(path)

# Setup the environment for django, so we can use the object model code for
# interfacing with the database.
os.environ["DJANGO_SETTINGS_MODULE"] = "mysite.settings"

site.addsitedir(os.path.join("..", "web", "mysite"))
import mysite, mysite.settings

django.setup()

from scanner.models import ScanInfo, ScanData

###

parser = argparse.ArgumentParser(
    description="Generates waterfall images from (general) scan data")
#parser.add_argument("-s", dest="scan_period", type=float, default=60,
#                    help="Time between scans (scan period)")
#parser.add_argument("-d", dest="date", type=str, default="",
#                    help="Date for scan")
parser.add_argument("date", type=str, help="Scan date (YYYY-MM-DD)")
parser.add_argument("start", type=float, help="Start frequency")
parser.add_argument("stop", type=float, help="End frequency")
parser.add_argument("outfile", type=str)
args = parser.parse_args()

# If the date string is an integer, it represents the number of days into
# the past to use as a basis for a date.
try:
    offset = int(args.date)
except:
    start_time = datetime.datetime.strptime(args.date, "%Y-%m-%d")
else:
    tm = datetime.datetime.now() - datetime.timedelta(offset)
    start_time = datetime.datetime(tm.year, tm.month, tm.day)

start_time = timezone.make_aware(start_time)
stop_time = start_time + datetime.timedelta(1)

#print start_time, stop_time
#for info in ScanInfo.objects.filter():
#    print timezone.localtime(info.scan_start)
#sys.exit()

q = (Q(freq_start__gte=args.start) & Q(freq_stop__lte=args.stop) &
     Q(scan_start__gte=start_time, scan_start__lte=stop_time))
info_list = ScanInfo.objects.filter(q)

# TODO - make sure every record has the same number of scan samples
# (rather than just trusting the first one)
w = ScanData.objects.filter(scan_info=info_list.first()).count()
h = info_list.count()

if (h == 0):
    print "No records found"
    sys.exit()

if (w == 0):
    print "No scan data samples found"
    sys.exit()

def map_to_colour(value, start, end):
    colours = [
        (0,0,0),
        (0,0,255),
        (0,255,0),
        (255,0,0),
    ]
    value = max(min(value, end), start)
    n = float(end-start)/(len(colours)-1)
    i = (value-start)/n

    colour1 = colours[int(i)]
    try:
        colour2 = colours[int(i)+1]
    except IndexError:
        return colour1

    w = i-int(i)
    return (
        int(colour2[0]*w + (1-w)*colour1[0]),
        int(colour2[1]*w + (1-w)*colour1[1]),
        int(colour2[2]*w + (1-w)*colour1[2]))

range_start = -40
range_stop = 20

max_power = -sys.maxint
min_power = sys.maxint

img = Image.new("RGB", (w, h))
for y, info in enumerate(info_list):
    print info.id, info.freq_start, info.freq_stop
    #ScanData.objects.filter(scan_info=info).count()

    for x, data in enumerate(ScanData.objects.filter(scan_info=info)):
        #n = (data.power - range_start) / (range_stop-range_start)
        #n = max(min(n, 1), 0)
        #img.putpixel((x, y), (int(n*255), int(n*255), int(n*255)))

        (r, g, b) = map_to_colour(data.power, range_start, range_stop)
        img.putpixel((x, y), (r, g, b))

        min_power = min(min_power, data.power)
        max_power = max(max_power, data.power)

print min_power, max_power
img.save(args.outfile)
