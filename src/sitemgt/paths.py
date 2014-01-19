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

BASE_DIR = os.environ["SITEPATH"]
DESC_FILE =  os.path.join(BASE_DIR, "svn/site/xml/SiteDescription.xml")
OUTPUT_DIR = os.path.join(BASE_DIR, "website/variable")
CHECKS_DIR = os.path.join(BASE_DIR, "checks")
DEPLOYMENT_FMT = os.path.join(BASE_DIR, "status/{}_deployment.xml")

