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


from .general import SiteObject, Health, GOOD, FAIL, FAULT, DEGD, UNKNOWN

#from .software import RepoApplication, NonRepoApplication
import sitemgt

import os
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
        self.type = 'deployment'
        self.status = "Unknown"
        self.name = component.name + '@' + host.name
        self.requirements = {}
        # Initialize bi directional linkages
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
        requirement.deployments[self.name] = self
    
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
                       'NotConfigured':DEGD, 'DependencyProblem':''}

   
    def health(self):
        """Determines health of the deployment, based on own state and dependents.
        Note this function may change status, if dependents drive health"""

        if self._health is None:
            # While we may be recursing set our own health to the native value 
            self._health = self._possibleStates[self.status]
            
            #Now see if any dependent is worst than we are
            for dep_name in self.component.dependencies.keys():
                if dep_name in self.host.expected_deployments:
                    dep_health = self.host.expected_deployments[dep_name].health()
                    if Health.worst(dep_health,self._health) is not self._health:
                        self._health = Health.worst(dep_health,self._health)
                        self.status = "DependencyProblem"
        return self._health


    def functionalHealth(self):
        """Returns the functional health of the deployment, i.e. the worst of the component
        and the installation of the component"""
        if Health.worst([self.component.health(),self.health()]) is not self.health():
            return self.component.health()
        else:
            return self.health()

    def functionalStatus(self):
        """Returns the functional status of the deployment, i.e. the worst of the component
        and the installation of the component"""
        if Health.worst([self.component.health(),self.health()]) is not self.health():
            return "Component " + self.component.status
        else:
            return self.status


    def gatherStatus(self, installed_package_tuples, cm_working_root):
        """Determines current state of the deployment, assuming we running on the host"""
        if isinstance(self.component, sitemgt.RepoApplication):
            # For repo apps build a list of installed packages
            self.installed_packages = list(set(self.component.package) & set([t[0] for t in installed_package_tuples]))
            if len(self.installed_packages) == len(self.component.package):
                self.status = "Installed"
            elif len(self.installed_packages) == 0:
                self.status = "Missing"
            else:
                self.status = "PartiallyInstalled"
        elif isinstance(self.component, sitemgt.NonRepoApplication):
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


    def resetStatus(self):
        """Resets the current status to Unknown"""
        self.status = "Unknown"
        self.resetHealth()
        if hasattr(self,'error'): delattr(self,'error')
        if hasattr(self,'installed_packages'): delattr(self,'installed_packages')
        
    def saveStatus(self, tag_writer):
        """Dumps the current status into the supplied XML tag writer object"""
        if hasattr(self,'status'):
            attributes = 'name="{}" status="{}"'.format(self.component.name, self.status)
            if hasattr(self,'error'): attributes += ' error="{}"'.format(self.error)
            tag_writer.open('Deployment',attributes)
            if hasattr(self,'installed_packages'):
                for pkg in self.installed_packages:
                    tag_writer.write('Installed','name="{}"'.format(pkg))
            tag_writer.close()
        
    def loadStatus(self,x_element):      
        """Load the current status from the supplied XML element object"""
        self.resetStatus()
        if x_element.get('status') is not None:
            self.status = x_element.get('status')
            if x_element.get('error') is not None:
                self.error = x_element.get('error')
            if isinstance(self.component, sitemgt.RepoApplication):
                self.installed_packages = [x_i.get('name') for x_i in x_element.findall('Installed')]
 
    def missingPackages(self):
        """Returns a list of all expected but not installed packages"""
        if hasattr(self,'installed_packages'):
            return list(set(self.component.package) - set(self.installed_packages))
        else:
            return []

    def verboseStatus(self):
        """Returns a status string including the error where one exists"""
        return self.status + (" ({})".format(self.error) if hasattr(self,'error') else '')
    
        