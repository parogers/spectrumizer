# gsm.py

import sys
import select
import os
import subprocess
import time
import collections
from Queue import Empty

# How many seconds without seeing any packets since starting scan
NO_CAPTURE_TIMEOUT = 5
GSM_STEP = 200
#GRGSM_CAPTURE_PATH = os.path.join("/", "usr", "local", "bin",
#                                  "grgsm_capture.py")
#GRGSM_DECODE_PATH = os.path.join("/", "usr", "local", "bin", "grgsm_decode")
#
GRGSM_CAPTURE_PATH = "grgsm_capture.py"
GRGSM_DECODE_PATH = "grgsm_decode"
#GRGSM_LIVEMON_PATH = os.path.join("..", "contrib", "grgsm_nogui_livemon_old.py")
GRGSM_LIVEMON_PATH = os.path.join("..", "contrib", "grgsm_nogui_livemon.py")

# TODO fill this in
GSM_BANDS = {
    "GSM850" : (869.2, 893.8),
    "PCS1900" : (1930.2, 1989.8),
}

class CellInfo(object):
    frequency = 0
    cellid_list = None
    complete = True
    cell_desc = None
    neighbours = None
    neighbours_ext = None
    arfcn = None
    cellid = None

    def __init__(self):
        self.cellid_list = set()
        self.neighbours = []
        self.neighbours_ext = []
        self.cell_desc = []

    def cellid_consistent(self):
        #return (not self.cellid_list or
        #        all(cellid == self.cellid_list[0]
        #            for cellid in self.cellid_list))
        return len(self.cellid_list) <= 1

    def add_cellid(self, mcc, mnc, lac, cellid):
        #info.cellid_list.append((mcc, mnc, lac, cellid))
        args = (mcc, mnc, lac, cellid)
        if (not self.cellid):
            # Track the first cell ID observed
            self.cellid = args
        self.cellid_list.add(args)

def dump_cell_info(cell):
    if (cell.cellid):
        # Output cellid information
        if (cell.cellid_consistent()):
            (mcc, mnc, lac, cellid) = cell.cellid
            print("[*] Cell (%0.1f MHz) = %d/%d/%d/%d" % (
                cell.frequency, mcc, mnc, lac, cellid))
        else:
            print("[*] Cell (%0.1f MHz) = %s" % (
                cell.frequency, cell.cellid_list))

    elif (not cell.complete):
        # Found a GSM signal
        print("[*] Cell (%0.1f MHz) = Scan not complete" % cell.frequency)

    else:
        # Found a GSM signal
        print("[*] Cell (%0.1f MHz) = GSM signal found" % cell.frequency)

    if (cell.arfcn):
        print "->  ARFCN = %s" % cell.arfcn
    if (cell.cell_desc):
        print "->  Cell description = %s" % (",".join(cell.cell_desc))
    if (cell.neighbours):
        print "->  Neighbours = %s" % (",".join(cell.neighbours))
    if (cell.neighbours_ext):
        print "->  Extended neighbours = %s" % (
            ",".join(cell.neighbours_ext))

# filetype is either "burst" or "cfile"
def capture_gsm_data(scan_path, freq, duration=5, gain=1):
    stdout = ""
    stderr = ""
    errno = -1
    if (os.path.exists(scan_path)):
        os.unlink(scan_path)

    args = [GRGSM_CAPTURE_PATH,
            "-g", str(gain),
            "-T", str(duration),
            "-f", str(freq) + "M"]
    if (scan_path.endswith(".bfile")):
        args += ["-b", scan_path]
    elif (scan_path.endswith(".cfile")):
        args += ["-c", scan_path]
    else:
        raise Exception("Invalid file type to save: %s" % filetype)

    proc = subprocess.Popen(
        args,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE)
    # Busy-wait loop to make sure the capture process finishes, or we kill
    # it if it takes too long.
    killed = False
    start = time.time()
    timeout = time.time() + duration + 40
    while (proc.poll() == None):
        time.sleep(0.1)
        if (time.time() > timeout):
            print "WARNING: scan taking too long..."
            while (proc.poll() == None):
                if (time.time() > timeout + 15):
                    print "ERROR: killing scan process"
                    killed = True
                    proc.kill()
                    break
            break
    print "Took", (time.time()-start)
    (stdout, stderr) = proc.communicate()
    errno = proc.returncode
    if (errno != 0):
        if (killed):
            e = OSError("process killed because scan took too long")
        else:
            e = OSError("gsm capture failure")
        e.stdout = stdout
        e.stderr = stderr
        e.errno = errno
        raise e

def analyze_gsm_data(scan_path, freq, recv_queue, duration=0):
    info = CellInfo()
    info.frequency = freq

    print("Analyzing traffic...")
    proc = subprocess.Popen(
        [GRGSM_DECODE_PATH,
         "-b", scan_path,
         "-f", str(freq) + "M"],
         stderr=subprocess.PIPE,
         stdout=subprocess.PIPE)

    timeout = None
    warn = False
    start = time.time()
    while True:
        time.sleep(0.05)
        # Wait for the GSM decoder to finish execution
        if (not timeout and proc.poll() != None):
            # Wait another few seconds for any stray packets still yet to come
            timeout = time.time() + 3

        if (timeout and time.time() > timeout):
            break

        if (duration and not warn and time.time() - start > 5+3*duration):
            print "WARNING: analysis taking too long..."
            warn = True
        if (duration and time.time() - start > 5+4*duration):
            print "ERROR: killing GSM analyzer"
            proc.kill()
            info.complete = False
            break

        try:
            data = recv_queue.get_nowait()
        except Empty:
            pass
        else:
            if (data[0] == "FAIL"):
                print ""
                print "ERROR: capture failed (%s) with error: %s" % (
                    data[1], data[2])
                print "(check permissions on capture)"
                print ""
                break

            if (data[0] == "ID"):
                # Cell ID information
                (code, mcc, mnc, lac, cellid) = data
                info.add_cellid(mcc, mnc, lac, cellid)

            elif (data[0] == "CELL-DESC"):
                info.cell_desc = data[1:]

            elif (data[0] == "NEIGHBOURS"):
                info.neighbours = data[1:]

            elif (data[0] == "NEIGHBOURS-EXT"):
                info.neighbours_ext = data[1:]

            elif (data[0] == "ARFCN"):
                info.arfcn = data[1]

    print("Analysis time: %0.1fs" % (time.time() - start))
    return info

def live_capture_data(recv_queue, freq, duration, gain, scan_path=None, extra_time=0):
    args = [
        GRGSM_LIVEMON_PATH,
        "-g", str(gain),
        "-f", str(freq*1e6)
    ]
    if (scan_path):
        # Also log the captured data to a cfile
        args += ["-O", scan_path]
    proc = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE)
    start = time.time()
    info = CellInfo()
    info.frequency = freq
    found = False
    out = ""
    err = ""
    while time.time() - start < duration + extra_time:
        if (not found and time.time() - start > NO_CAPTURE_TIMEOUT):
            # Probably nothing here
            break

        if (info.cellid and time.time()-start > duration):
            # We've got the cellid info within the alloted time
            break
        
        (rds, _, _) = select.select([proc.stdout, proc.stderr], [], [], 0.1)
        if (proc.stdout in rds):
            ch = proc.stdout.read(1)
            if (not ch):
                break
            out += ch
        if (proc.stderr in rds):
            ch = proc.stderr.read(1)
            if (not ch):
                break
            err += ch
        try:
            data = recv_queue.get_nowait()
        except Empty:
            pass
        else:
            found = True
            if (data[0] == "FAIL"):
                print ""
                print "ERROR: capture failed (%s) with error: %s" % (
                    data[1], data[2])
                print "(trying checking permissions)"
                print ""
                break

            elif (data[0] == "ID"):
                # Cell ID information
                (code, mcc, mnc, lac, cellid) = data
                info.add_cellid(mcc, mnc, lac, cellid)

            elif (data[0] == "CELL-DESC"):
                info.cell_desc = data[1:]

            elif (data[0] == "NEIGHBOURS"):
                info.neighbours = data[1:]

            elif (data[0] == "NEIGHBOURS-EXT"):
                info.neighbours_ext = data[1:]

            elif (data[0] == "ARFCN"):
                info.arfcn = data[1]

            elif (data[0] == "PACKET"):
                pass

        #if (all((info.cellid, info.cell_desc, info.neighbours,
        #         info.neighbours_ext))): break
        #if (info.cellid):
        #    break

    print "Done after %0.1f seconds" % (time.time()-start)
    sys.stdout.flush()
    try:
        # Tell the capture process to finish
        proc.stdin.write("\n")
    except IOError:
        pass
    # Wait for the process to quit, and kill it if necessary
    t = time.time()
    while (proc.poll() == None):
        if (time.time() - t > 5):
            # Taking too long
            print "ERROR - killing capture process (quit taking too long)"
            proc.kill()
            break

    if (proc.returncode != None and proc.returncode != 0):
        print "ERROR: %s returned error code %s" % (
            GRGSM_LIVEMON_PATH, proc.returncode)
        print ""
        print "*** STDOUT ***"
        print ""
        print out
        print ""
        print "*** STDERR ***"
        print ""
        print err
        print ""

    if (not found):
        return None
    return info

def store_and_analyze_data(recv_queue, freq, duration, gain):
    # Make a number of attempts to capture the data
    tries = 3
    scan_path = os.path.join("/", "run", "user", str(os.getuid()), "out.bfile")
    for n in range(tries):
        try:
            capture_gsm_data(
                scan_path, freq,
                duration=duration,
                gain=gain)
            break
        except OSError as e:
            print("ERROR: failed to capture data (errno=%d)" % e.errno)
            print("")
            print("*STDOUT*")
            print("")
            print(e.stdout)
            print("")
            print("*STDERR*")
            print("")
            print(e.stderr)
            print ""
            time.sleep(1)
    else:
        print("ERROR: too many failed capture attempts")
        return None

    if (os.stat(scan_path).st_size == 0):
        print "WARNING: no GSM signal detected, skipping..."
        print ""
        return None

    info = analyze_gsm_data(
        scan_path, freq, recv_queue, duration=duration)
    return info
