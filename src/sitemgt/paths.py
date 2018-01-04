#========================================================
# paths.py
#========================================================
# PublicPermissions: True
#========================================================
# Defines local and relative paths for key site
# management locations
#========================================================

__author__="Jody"
__date__ ="$Date:$"

import os
import subprocess

SITE_BASE_DIR = os.environ["SITEPATH"]
SITE_XML_FILE =  os.path.join(SITE_BASE_DIR, "svn/site/xml/SiteDescription.xml")
WEB_OUTPUT_DIR = os.path.join(SITE_BASE_DIR, "website/variable")
CHECK_RESULTS_DIR = os.path.join(SITE_BASE_DIR, "checks")
CHECK_SRC_DIR = os.path.join(SITE_BASE_DIR, "svn/site/checks")
CM_WORKING_DIR = os.path.join(SITE_BASE_DIR, "svn")

def getDeploymentFile(host_name):
    """Return the qualified path name of the deployment record for the specified host"""
    return os.path.join(SITE_BASE_DIR, "status/{}_deployment.xml".format(host_name))

def getStatusReportFile(host_name):
    """Return the qualified path name of the deployment record for the specified host"""
    return os.path.join(SITE_BASE_DIR, "status/{}_status_report.xml".format(host_name))

# Note these two functions are pretty fragile. Cannot afford to have multiple scripts that 
# using them in parallel, errors will be thrown up to the caller, and we rely on the environment 
# variable being mounted directly. All that said the effect of failure is pretty benign.

def mountSiteDir():
    """Mount the site directory if it is not currently mounted. Returns a token which may
    be passed to unmountSiteDir to ensure a symmetric response"""
    mounts = subprocess.check_output(["mount"]).decode("utf-8").split("\n")
    if len([m for m in mounts if (" " + SITE_BASE_DIR + " ") in m]) == 0:
        # Site path not found in mount table, do the mount - this may fail if not root
        subprocess.check_output(["mount",SITE_BASE_DIR])
        return True
    else:
        return False

def unmountSiteDir(token): 
    """Unmount the site directory if the token passed from mountSiteDir indicates a mount 
    was performed"""
    if token is True:
        subprocess.check_output(["umount",SITE_BASE_DIR])