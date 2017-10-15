from __future__ import unicode_literals

from django.db import models

# A session is a collection of scans that all "belong together".
# This is used to generate waterfall plots
class ScanSession(models.Model):
    # Frequency range of the scan (Hz)
    freq_start = models.IntegerField("starting frequency")
    freq_stop = models.IntegerField("stopping frequency")
    # Keywords associated with the scan
    keywords = models.CharField("keywords", max_length=255)
    # General notes about the scan
    notes = models.TextField("notes")
    # The device and tuner used to obtain this info scan
    capture_device = models.CharField(max_length=64, default="")
    capture_tuner = models.CharField(max_length=64, default="")
    # The gain setting for the capture device during scan
    gain = models.FloatField(default=0)

# Meta data for a single snapshot of the spectrum
class SnapshotInfo(models.Model):
    scan_session = models.ForeignKey(ScanSession, on_delete=models.CASCADE)
    scan_start = models.DateTimeField("scan start")
    scan_stop = models.DateTimeField("scan stop", default=None)

# Scan data for a single frequency
class ScanData(models.Model):
    snapshot_info = models.ForeignKey(SnapshotInfo, on_delete=models.CASCADE)
    # The measured frequency (Hz) and magnitude
    frequency = models.IntegerField("frequency")
    power = models.FloatField("power")
