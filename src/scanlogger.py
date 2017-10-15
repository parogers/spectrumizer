#!/usr/bin/env python

import time
import math
import sys
import argparse

from rtlpower import rtlpower

class ScanWindow(object):
    power_window = None
    window_size = 10

    def __init__(self, window_size):
        self.power_window = []
        self.window_size = window_size

    def add(self, samples):
        self.power_window.append(samples)
        self.power_window = self.power_window[-self.window_size:]

    def average(self):
        """Returns an average for data points in the window"""
        assert(self.power_window)
        for samples in zip(*self.power_window):
            yield sum(samples)/float(len(samples))

###

if (__name__ == "__main__"):
    parser = argparse.ArgumentParser(description="Wrapper for rtl_power")
    parser.add_argument("-s", dest="scan_period", type=float, default=10,
                        help="Time between scans (scan period)")
    parser.add_argument("-i", dest="interval", type=float, default=1,
                        help="Scan integration interval")
    parser.add_argument("-g", dest="gain", type=float, default=1)
    parser.add_argument("-r", dest="res", type=float, default=200)
    parser.add_argument("start", type=float)
    parser.add_argument("stop", type=float)
    args = parser.parse_args()

    if (args.scan_period < args.interval):
        parser.print_help()
        print ""
        print "Scan period must be greater than integration interval"
        sys.exit(-1)

    scan_count = 0
    # The various scan windows
    windows = [
        ScanWindow(1*60//args.scan_period+1),
        ScanWindow(5*60//args.scan_period+1),
        ScanWindow(30*60//args.scan_period+1)
    ]

    #for win in windows:
    #    print "Window: %d samples (%0.1f minutes)" % (
    #        win.window_size,
    #        win.window_size * args.scan_period/60.0)

    start = time.time()
    while True:
        sys.stderr.write("Scan %d\n" % scan_count)
        power_data = list(rtlpower(
            args.start, args.stop,
            scan_interval=args.interval,
            gain=args.gain,
            res=args.res))

        (freq_list, pwr_samples) = zip(*power_data)
        for win in windows:
            win.add(pwr_samples)

        #print " ".join("%0.1f" % pwr for pwr in windows[0].average())

        if (scan_count % windows[0].window_size == 0):
            averages = [list(win.average()) for win in windows]

            for n, freq in enumerate(freq_list):
                print ("%0.3f "%freq) + " ".join("%0.2f" % (avg[n]) for avg in averages)

            print ""
            print ""

        scan_count += 1

        # Wait for the next scan to happen
        next_time = scan_count*args.scan_period + start
        #sys.stderr.write("Delay %f\n" % (next_time - time.time()))
        time.sleep(next_time - time.time())
