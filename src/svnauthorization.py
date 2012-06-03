#========================================================
# svnauthorization.py
#========================================================
# $HeadURL:                                             $
# Last $Author: jody $
# $Revision: 742 $
# $Date: 2009-12-28 02:23:37 -0600 (Mon, 28 Dec 2009) $
#========================================================
# PublicPermissions: True
#========================================================
# Simple class to gather authority to access the 
# subversion repositories, either by reading the standard
# file or by prompting the user
#========================================================

# Define constants
PWD_FILE = "~/.subversion_password"             # Text file for subversion username/password

import os

class SvnAuthorization(object):
    """Simple class to gather and report a subversion username/password pair"""
    
    def __init__(self):
        (self.username, self.password) = (None, None)

    def readFromFile(self,filename = PWD_FILE):
        self.filename = filename.replace('~',os.environ["HOME"])
        if os.path.exists(self.filename):
            f = open(self.filename)
            params = f.read().strip().split('=')
            f.close()
            if len(params)==2:
                (self.username,self.password) = params
                return True
        return False
        
    def readFromTerminal(self):
        self.username = input("Please enter subversion username: ")
        self.password = input("Please enter subversion password: ")
        return True

    def subversionParams(self):
        """Returns the standard parameters for a subversion including authorization"""
        return "--non-interactive --no-auth-cache --username {} --password {}".format(self.username,self.password)
