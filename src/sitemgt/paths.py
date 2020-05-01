#========================================================
# paths.py
#========================================================
# PublicPermissions: True
#========================================================
# Defines local and relative paths for key site
# management locations
#========================================================

import os
import subprocess
from subprocess import DEVNULL

SITE_BASE_DIR = os.environ["SITEPATH"]

SITE_XML_FILE =  os.path.join(SITE_BASE_DIR, "repo/site/xml/SiteDescription.xml")
WEB_OUTPUT_DIR = os.path.join(SITE_BASE_DIR, "website/variable")
CHECK_RESULTS_DIR = os.path.join(SITE_BASE_DIR, "checks")
CHECK_SRC_DIR = os.path.join(SITE_BASE_DIR, "repo/site/checks")
CM_WORKING_DIR = os.path.join(SITE_BASE_DIR, "repo")
CM_UPSTREAM_DIR = os.path.join(SITE_BASE_DIR, "repo.git")

def getDeploymentFile(host_name):
    """Return the qualified path name of the deployment record for the specified host"""
    return os.path.join(SITE_BASE_DIR, "status/{}_deployment.xml".format(host_name))

def getStatusReportFile(host_name):
    """Return the qualified path name of the deployment record for the specified host"""
    return os.path.join(SITE_BASE_DIR, "status/{}_status_report.xml".format(host_name))

# Note these two functions are pretty fragile. Cannot afford to have multiple scripts that
# using them in parallel, errors will be thrown up to the caller, and we rely on the environment
# variable being mounted directly. All that said the effect of failure is pretty benign.

class MountedSiteDirectories(object):
    """Simple context manager class to mount any unmounted filesystem mounts referencing
    the site path, then unmount the same set at completion."""

    @staticmethod
    def _defined_mounts():
        """Returns all the site mountpoints defined in fstab."""
        lines = subprocess.check_output(['findmnt', '--fstab', '--noheadings', '--list',
                                         '--output', 'TARGET']).decode('utf-8').split()
        return set([line for line in lines if line.startswith(SITE_BASE_DIR)])

    @staticmethod
    def _mounted_mounts():
        """Returns all the site mountpoints currently mounted."""
        lines = subprocess.check_output(['findmnt', '--kernel', '--noheadings', '--list',
                                         '--output', 'TARGET']).decode('utf-8').split()
        return set([line for line in lines if line.startswith(SITE_BASE_DIR)])

    def __init__(self):
        self.mounted = set()

    def __enter__(self):
        for mount in set.difference(self._defined_mounts(), self._mounted_mounts()):
            if subprocess.call(['mount', mount], stdout=DEVNULL, stderr=DEVNULL) == 0:
                self.mounted.add(mount)
            else:
                raise Exception('Failed to mount site at {}'.format(mount))

    def __exit__(self, type, value, traceback):
        for mount in self.mounted:
            if subprocess.call(['umount', mount], stdout=DEVNULL, stderr=DEVNULL) == 0:
                self.mounted.remove(mount)
