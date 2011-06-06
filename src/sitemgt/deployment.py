#========================================================
# software.py
#========================================================
# $HeadURL:                                             $
# Last $Author: jody $
# $Revision: 742 $
# $Date: 2009-12-28 02:23:37 -0600 (Mon, 28 Dec 2009) $
#========================================================
# Classes to represent and assess the deployment of a 
# software component onto hardware hosts
#========================================================


from .general import SiteObject, GOOD, FAIL, FAULT, DEGD, UNKNOWN
from .software import RepoApplication, NonRepoApplication

import os
#import subprocess
import time
import filecmp

class _ComparisonState(object):
    """Determines and stores state of comparison between two files"""
    MATCH = 0
    ERROR = 1
    NO_LOCAL_FILE = 2
    MASTER_FILE_NEWER = 3
    LOCAL_FILE_NEWER = 4
    NO_MASTER_FILE = 5
    
    def __init__(self,local_path,master_path):
        """Determine relative state of supplied path"""
        if not os.path.exists(local_path):
            self.state = _ComparisonState.NO_LOCAL_FILE if os.path.exists(master_path) else _ComparisonState.ERROR
        elif not os.path.exists(master_path):
            self.state = _ComparisonState.NO_MASTER_FILE
        elif filecmp.cmp(local_path, master_path):
            self.state = _ComparisonState.MATCH
        else:
            local_time = time.ctime(os.path.getmtime(local_path))
            master_time = time.ctime(os.path.getmtime(master_path))
            self.state =  _ComparisonState.LOCAL_FILE_NEWER if local_time > master_time else _ComparisonState.MASTER_FILE_NEWER


#class _SvnLocalState(object):
#    """Determines and stores state of a subversion working file"""
#    GOOD = 0
#    ERROR = 1
#    NO_LOCAL_FILE = 2
#    ABNORMAL = 3
#    MODIFIED = 4
#    OUT_OF_DATE = 5
#    
#    def __init__(self,path):
#        """Determine state of supplied path"""
#        self.path = path
#        if not os.path.exists(self.path):
#            self.state = _SvnLocalState.NO_LOCAL_FILE
#        else:
#            (self.return_code,output) = subprocess.getstatusoutput('svn -vu --non-interactive "{}"'.format(path))
#            self.state_string = output[:9]
#            if self.return_code != 0 :
#                self.state = _SvnLocalState.ERROR
#            else:
#                if self.state_string[1:7] != '      ':  self.state = _SvnLocalState.ABNORMAL
#                elif self.state_string[8] == '*':       self.state = _SvnLocalState.OUT_OF_DATE
#                elif self.state_string[0] == ' ':       self.state = _SvnLocalState.GOOD
#                elif self.state_string[0] == 'M':       self.state = _SvnLocalState.MODIFIED
#                elif self.state_string[0] == 'A':       self.state = _SvnLocalState.MODIFIED
#                elif self.state_string[0] == '?':       self.state = _SvnLocalState.ERROR
#                else:                                   self.state = _SvnLocalState.ABNORMAL
#
#class _SvnRemoteState(object):
#    """Determines and stores state of a subversion repository file"""
#    EXISTS = 0
#    DOES_NOT_EXIST = 1
#    COMM_FAIL = 2
#    
#    def __init__(self,repository,location):
#        """Determine state of supplied location within supplied repository"""
#        self.url = "svn://" + os.path.join(repository,location)
#        retcode = subprocess.getstatusoutput('svn --non-interactive list "{}"'.format(self.url))[0]
#        if retcode == 0:
#            self.state = _SvnRemoteState.EXISTS
#        else:
#            # Could not find that file, but does the mean the file is bad or the whole repository is down?
#            retcode = subprocess.getstatusoutput('svn --non-interactive list "svn://{}"'.format(repository))[0]
#            if retcode == 0:
#                self.state = _SvnRemoteState.DOES_NOT_EXIST
#            else:
#                self.state = _SvnRemoteState.COMM_FAIL

#class _RepoPackageState(object):
#    """Determines and stores install state of a debian package"""
#    INSTALLED = 0
#    NOT_INSTALLED = 1
#    
#    def __init__(self,package):
#        """Determine state of supplied location within supplied repository"""
#        output = subprocess.check_output("aptitude search '~n^{}$ ~i'".format(package),shell=True)
#        self.state = _RepoPackageState.INSTALLED if len(output) > 1 else _RepoPackageState.NOT_INSTALLED 


class Deployment(SiteObject):
    """Represents a deployment of a software component onto a hardware host, initialized either
    manually (if inferred from a requirement), or from an XML object (if explicit in XML)"""

    def __init__(self, host, component, location = None):
        """Initialize object"""
        # Initialize bi directional linkages
        self.type = 'deployment'
        self.name = component.name + '>>' + host.name
        self.requirements = {}
        self.host = host
        host.expected_deployments[component.name] = self
        self.component = component
        component.deployments[host.name] = self
        # Initialize primitives
        if location is not None:
            self.location = location
        elif hasattr(self.component, 'installLocation'):
            self.location = self.component.installLocation
    
    def _addRequirement(self,requirement):
        """Link the Deployment as being driven by the specified requirement"""
        self.requirements[requirement.uid] = requirement
        requirement.components[self.component.name] = self.component
    
    def locationDescription(self):
        """Returns a string assessment of the deployment location""" 
        if hasattr(self, 'location'):
            return self.location
        elif hasattr(self.component, 'package'): 
            return 'Via Repository'
        else:
            return 'Unknown'


    _possibleStates = {'Installed':GOOD, 'Missing':FAIL, 'PartiallyInstalled':DEGD,
                       'ModifiedLocally':FAULT, 'OutOfDate':DEGD, 'Unknown': UNKNOWN,
                       'NotConfigured':DEGD }

    def gatherState(self, installed_package_tuples, cm_working_root):
        """Determines current state of the deployment, assuming we running on the host"""
        if isinstance(self.component, RepoApplication):
            # For repo apps build a list of installed packages
            self.installed_packages = list(set(self.component.package) & set([t[0] for t in installed_package_tuples]))
            if len(self.installed_packages) == len(self.component.package):
                self.status = "Installed"
            elif len(self.installed_packages) == 0:
                self.status = "Missing"
            else:
                self.status = "PartiallyInstalled"
        elif isinstance(self.component, NonRepoApplication):
            # For non repo apps can only check existence of a path 
            if hasattr(self.component,"install_location"):
                if os.path.exists(self.component.install_location):
                    self.status = "Installed"
                else:
                    self.status = "Missing"
            else:
                self.status = "Unknown"
                self.error = "No install_location to test for NonRepoApplication"
        else:
            # For CM based files check the relative state of the deployed file against the
            # up to date working copy of the repository
            cm_working_path = os.path.join(cm_working_root, self.component.cm_location, self.component.cm_filename)
            cmp = _ComparisonState(self.location,cm_working_path)
            
            if cmp.state == _ComparisonState.MATCH:                 self.status = "Installed"
            elif cmp.state == _ComparisonState.NO_LOCAL_FILE:       self.status = "Missing"
            elif cmp.state == _ComparisonState.LOCAL_FILE_NEWER:    self.status = "ModifiedLocally"
            elif cmp.state == _ComparisonState.MASTER_FILE_NEWER:   self.status = "OutOfDate"
            elif cmp.state == _ComparisonState.NO_MASTER_FILE:      self.status = "NotConfigured"
            else:
                self.status = "Unknown"
                self.error = "Neither local or CM copies found"
    


    def missingPackages(self):
        """Returns a list of all expected but not installed packages"""
        if hasattr(self,'installed_packages'):
            return list(set(self.component.package) - set(self.installed_packages))
        else:
            return []
        