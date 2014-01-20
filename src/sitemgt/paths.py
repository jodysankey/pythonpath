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

SITE_BASE_DIR = os.environ["SITEPATH"]
SITE_XML_FILE =  os.path.join(SITE_BASE_DIR, "svn/site/xml/SiteDescription.xml")
WEB_OUTPUT_DIR = os.path.join(SITE_BASE_DIR, "website/variable")
CHECK_RESULTS_DIR = os.path.join(SITE_BASE_DIR, "checks")
CHECK_SRC_DIR = os.path.join(SITE_BASE_DIR, "svn/site/checks")
DEPLOYMENT_FMT = os.path.join(SITE_BASE_DIR, "status/{}_deployment.xml")

