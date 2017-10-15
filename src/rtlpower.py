#!/usr/bin/env python3

import traceback
import signal
import os
import select
import re
import argparse
import subprocess
import sys
import time

class RTLPowerResult:
    tuner = ""
    device = ""
    samples = None

    def __init__(self):
        self.samples = []

    def __iter__(self):
        return iter(self.samples)

    def __getitem__(self, n):
        return self.samples[n]

    def __len__(self):
        return len(self.samples)

def rtlpower(start_freq, stop_freq,
             scan_interval=5, gain=1,
             res=200, timeout=None):
    # rtl_power doesn't like when the frequency range has zero width. We need
    # to give it a range that is greater than the frequency "resolution".
    if (stop_freq - start_freq < res/1e3):
        stop_freq = start_freq + (res/1e3)*1.01

    proc = subprocess.Popen([
        "rtl_power",
        "-c", "30%",
        "-1",
        "-i", str(scan_interval),
        "-g", str(gain),
        "-f", "%fM:%fM:%fk" % (start_freq, stop_freq, res),
        "-"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    out = ""
    err = ""
    start = time.time()
    while True:
        (rds, wrts, ex) = select.select((proc.stdout, proc.stderr), (), (), 1)
        if (proc.stdout in rds):
            data = proc.stdout.readline().decode("UTF-8")
            if (not data): break
            out += data
        elif (proc.stderr in rds):
            line = proc.stderr.readline().decode("UTF-8")
            err += line
            if (line.strip() == "Error: bad retune."):
                proc.terminate()
                proc.wait()
                e = OSError("rtl_power device failure: bad retune error")
                e.stdout = out
                e.stderr = err
                raise e

        if (timeout and time.time()-start > timeout):
            # Timeout happened before rtl_power finished, so kill it now
            #print("rtl_power taking too long, sending SIGTERM")
            proc.terminate()
            # So the process doesn't always die with SIGTERM, so we wait
            # here a while then fire off SIGKILL
            start = time.time()
            while proc.poll() == None:
                if (time.time()-start > 10):
                    #print("rtl_power not dying, sending SIGKILL")
                    os.kill(proc.pid, signal.SIGKILL)
                    break
            #print("collecting rtl_power")
            proc.wait()
            e = OSError("rtl_power hung (timeout)")
            e.stdout = out
            e.stderr = err
            raise e

    proc.wait()
    #(out, err) = proc.communicate()

    if (proc.returncode != 0):
        e = OSError("rtl_power failed (return code %d)" % proc.returncode)
        e.stdout = out
        e.stderr = err
        raise e

    result = RTLPowerResult()
    for line in err.strip().split("\n"):
        m = re.match("Found (.*) tuner", line)
        if (m):
            result.tuner = m.groups()[0]
        m = re.match("Using device \d+: (.*)", line)
        if (m):
            result.device = m.groups()[0]

    for line in out.strip().split("\n"):
        args = line.split(", ")
        (date, tm, start, stop, step, _) = args[0:6]
        start = float(start)
        stop = float(stop)
        step = float(step)
        samples = args[6:]
        for (n, sample) in enumerate(samples):
            freq = start + n*step
            result.samples.append((freq, float(sample)))

    if (not result.samples):
        e = ValueError("rtl_power exited with success, but failed to output samples")
        e.stdout = out
        e.stderr = err
        raise e

    return result

if (__name__ == "__main__"):
    parser = argparse.ArgumentParser(description="Wrapper for rtl_power")
    parser.add_argument("-i", dest="interval", type=float, default=5,
                        help="Scan integration interval")
    parser.add_argument("-g", dest="gain", type=float, default=1)
    parser.add_argument("-r", dest="res", type=float, default=200)
    parser.add_argument("start", type=float)
    parser.add_argument("stop", type=float)
    args = parser.parse_args()

    try:
        for (freq, power) in rtlpower(
                args.start, args.stop,
                scan_interval=args.interval,
                gain=args.gain,
                res=args.res):
            print("%0.6f %0.2f" % (freq, power))
    except Exception as e:
        print("***EXCEPTION***")
        #print(e)
        traceback.print_exc()
        if (hasattr(e, "stdout")):
            print("***STDOUT***")
            print(e.stdout)
        if (hasattr(e, "stderr")):
            print("***STDERR***")
            print(e.stderr)
