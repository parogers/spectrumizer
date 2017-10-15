# usbutil.py

import time
from fcntl import ioctl
import ctypes
import subprocess
import re

# List of known SDR devices (product/vendor pairs) taken from librtlsdr
# TODO - is there a better way of getting this data (ctypes doens't work...)
KNOWN_DEVICES = (
    (0x0bda, 0x2832),
    (0x0bda, 0x2838),
    (0x0413, 0x6680),
    (0x0413, 0x6f0f),
    (0x0458, 0x707f),
    (0x0ccd, 0x00a9),
    (0x0ccd, 0x00b3),
    (0x0ccd, 0x00b4),
    (0x0ccd, 0x00b5),
    (0x0ccd, 0x00b7),
    (0x0ccd, 0x00b8),
    (0x0ccd, 0x00b9),
    (0x0ccd, 0x00c0),
    (0x0ccd, 0x00c6),
    (0x0ccd, 0x00d3),
    (0x0ccd, 0x00d7),
    (0x0ccd, 0x00e0),
    (0x1554, 0x5020),
    (0x15f4, 0x0131),
    (0x185b, 0x0620),
    (0x185b, 0x0650),
    (0x185b, 0x0680),
    (0x1b80, 0xd393),
    (0x1b80, 0xd394),
    (0x1b80, 0xd395),
    (0x1b80, 0xd397),
    (0x1b80, 0xd398),
    (0x1b80, 0xd39d),
    (0x1b80, 0xd3a4),
    (0x1b80, 0xd3a8),
    (0x1b80, 0xd3af),
    (0x1b80, 0xd3b0),
    (0x1d19, 0x1101),
    (0x1d19, 0x1102),
    (0x1d19, 0x1103),
    (0x1d19, 0x1104),
    (0x1f4d, 0xa803),
    (0x1f4d, 0xb803),
    (0x1f4d, 0xc803),
    (0x1f4d, 0xd286),
    (0x1f4d, 0xd803)
)

def get_default_sdr_device():
    """Returns the USB capture device used by default"""
    # TODO - running rtl_eeprom causes stability problems later on
    # (resetting the device gives very inconsistent results after running)
    #
    # Run rtl_eeprom which gives us lots of information about the default
    #proc = subprocess.Popen(["rtl_eeprom"],
    #                        stdout=subprocess.PIPE,
    #                        stderr=subprocess.PIPE)
    #vendor_id = None
    #product_id = None
    #(out, err) = proc.communicate()
    #for line in err.split("\n"):
    #    try:
    #        (key, value) = line.split(":")
    #    except:
    #        pass
    #    else:
    #        if (key.strip() == "Vendor ID"):
    #            vendor_id = value.strip()[2:]
    #        elif (key.strip() == "Product ID"):
    #            product_id = value.strip()[2:]
    #if (not vendor_id or not product_id):
    #    return None

    # Run lsusb to get the bus and device number of the USB device
    proc = subprocess.Popen(["lsusb"], stdout=subprocess.PIPE)
    (out, err) = proc.communicate()
    for line in out.decode("UTF-8").split("\n"):
        m = re.match("Bus (\d*) Device (\d*): ID (\w\w\w\w):(\w\w\w\w)", line)
        if (m):
            (bus, devno, vendor_id, product_id) = m.groups()
            vendor_id = int(vendor_id, 16)
            product_id = int(product_id, 16)
            if ((vendor_id, product_id) in KNOWN_DEVICES):
                return (int(bus), int(devno))

    return None

def reset_sdr_device():
    """Resets the default USB SDR device"""
    try:
        (usb_bus, usb_dev) = get_default_sdr_device()
    except TypeError:
        raise IOError("Cannot find USB SDR device")
    reset_usb_device(usb_bus, usb_dev)

def reset_usb_device(bus, devno):
    path = "/dev/bus/usb/%03d/%03d" % (bus, devno)
    USBDEVFS_RESET = 21780
    with open(path, "w") as fd:
        ret = ioctl(fd, USBDEVFS_RESET, 0)
        if (ret < 0):
            raise OSError("Error calling ioctl (ret=%d)" % ret)
    time.sleep(0.5)
