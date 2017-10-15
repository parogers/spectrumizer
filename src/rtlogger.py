#!/usr/bin/env python3

import django
from django.utils import timezone
import datetime
import time
import math
import sys
import os
import site
import argparse
import select

from rtlpower import rtlpower
import usbutil

path = os.path.dirname(sys.argv[0])
if (path):
    os.chdir(path)

# Setup the environment for django, so we can use the object model code for
# interfacing with the database.
os.environ["DJANGO_SETTINGS_MODULE"] = "spectrumweb.settings"

site.addsitedir("spectrumweb")
import spectrumweb, spectrumweb.settings

django.setup()

# Now we can import the models for storing scan data
from scan.models import ScanSession, SnapshotInfo, ScanData

if (__name__ == "__main__"):
    parser = argparse.ArgumentParser(
        description="Wrapper for rtl_power, saves to database")
    parser.add_argument("-s", "--period", dest="scan_period", type=float, default=60,
                        help="Time between scans (default: %(default)s)")
    parser.add_argument("-i", "--interval", dest="interval", type=float, default=1,
                        help="Scan integration interval (default: %(default)s)")
    parser.add_argument("-d", "--duration", dest="duration", type=float, default=0,
                        help="Overall scan duration (default: %(default)s)")
    parser.add_argument("-1", "--single", dest="single", action="store_true",
                        help="Perform a single frequency scan", default=False)
    parser.add_argument("-g", "--gain", dest="gain",
                        help="Tuner gain (default: %(default)s)", type=float, default=1)
    parser.add_argument("-r", "--res", dest="res",
                        help="Scan resolution for rtl_power (default: %(default)s)",
                        type=float, default=200)
    parser.add_argument("-n", "--notes", dest="notes",
                        help="Optional note to include", type=str, default="")
    parser.add_argument("-k", "--keywords", dest="keywords",
                        help="Optional keywords", type=str, default="")
    parser.add_argument("start", type=float)
    parser.add_argument("stop", type=float)
    args = parser.parse_args()

    if (args.scan_period < args.interval):
        parser.print_help()
        print("")
        print("Scan period must be greater than integration interval")
        sys.exit(-1)

    scan_session = None
    scan_count = 1
    session_start = time.time()
    if (args.single):
        print("Scan duration: once")
    elif (args.duration != 0):
        print("Scan duration: %0.1fs" % args.duration)
        print("Press ENTER to quit")
    else:
        print("Scan duration: forever")
        print("Press ENTER to quit")

    while (args.duration == 0 or time.time()-session_start <= args.duration):
        # Check if the user wants to exit
        (rd, wrt, exc) = select.select([sys.stdin], [], [], 0)
        if (rd):
            break
        
        start = time.time()
        now = datetime.datetime.now()
        sys.stderr.write("Scan %d (%s)\n" % (
            scan_count, now.strftime("%I:%M %p")))
        # Reset the device now before we start scanning, because sometimes
        # the device dies and a reset seems to fix that.
        usbutil.reset_sdr_device()
        start_time = timezone.now()
        try:
            power_data = rtlpower(
                args.start, args.stop,
                scan_interval=args.interval,
                gain=args.gain,
                res=args.res,
                timeout=args.interval+30)
        except OSError as e:
            print("->Error running rtlpower (%s)" % e)
            traceback.print_exc()
            if hasattr(e, "stdout"):
                print("->STDOUT")
                print(e.stdout)
            if hasattr(e, "stderr"):
                print("->STDERR")
                print(e.stderr)
            print("->Sleeping for 120 seconds")
            time.sleep(120)
            continue
        stop_time = timezone.now()

        avg = sum(pwr for freq,pwr in power_data) / float(len(power_data))
        print("Average power: %0.1f" % avg)
        print("")

        if (not scan_session):
            #print("->Tuner: %s" % power_data.tuner)
            scan_session = ScanSession.objects.create(
                freq_start=args.start*1e6,
                freq_stop=args.stop*1e6,
                keywords=args.keywords,
                notes=args.notes,
                capture_device=power_data.device,
                capture_tuner=power_data.tuner,
                gain=args.gain)

        # Old versions of rtl_power will sometimes return NaN in power data
        if (any(math.isnan(pwr) for (freq, pwr) in power_data)):
            # Try again after a short delay
            print("->Error running rtlpower: NaN found in results, skipping...")
            time.sleep(10)
            continue

        snapshot = SnapshotInfo.objects.create(
            scan_session=scan_session,
            scan_start=start_time,
            scan_stop=stop_time)

        lst = []
        for (freq, pwr) in power_data:
            data = ScanData(
                snapshot_info=snapshot,
                frequency=freq,
                power=pwr)
            lst.append(data)

        ScanData.objects.bulk_create(lst)

        if (args.single): break

        # Wait for the next scan time
        tm = args.scan_period-(time.time()-start)
        if (tm > 0):
            if (tm > 2): print("(sleeping: %0.1f)" % tm)
            time.sleep(tm)
        scan_count += 1

print("Scanning complete")
print("Stored as session ID: %d" % scan_session.id)

