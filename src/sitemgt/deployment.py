#========================================================
# software.py
#========================================================
# PublicPermissions: True
#========================================================
# Classes to represent and assess the deployment of a
# software component onto hardware hosts
#========================================================

import os
import filecmp

from .general import SiteObject, Health, GOOD, FAIL, FAULT, DEGD, UNKNOWN
from .software import RepoApplication, NonRepoApplication, OtherFile


# TODO: I refactored the health from a function to a property, relying on the
# getHealthAndStatus function. Quite likely that this won't be working quite
# correctly for deployment since I didn't spend much time on it.

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
            local_time = os.path.getmtime(local_path)
            master_time = os.path.getmtime(master_path)
            self.state =  _ComparisonState.LOCAL_FILE_NEWER if local_time > master_time else _ComparisonState.MASTER_FILE_NEWER


class Deployment(SiteObject):
    """Represents a deployment of a software component onto a hardware host, initialized either
    manually (if inferred from a requirement), or from an XML object (if explicit in XML)"""

    _possibleStates = {'Installed':GOOD, 'Missing':FAIL, 'PartiallyInstalled':DEGD,
                       'ModifiedLocally':FAULT, 'OutOfDate':DEGD, 'Unknown': UNKNOWN,
                       'NotConfigured':DEGD, 'DependencyProblem':''}

    def __init__(self, host, component, location = None):
        """Initialize object"""
        self.type = 'deployment'
        self._status = "Unknown"
        self.name = component.name + '@' + host.name
        self.primary_requirements = {}
        self.secondary_requirements = {}
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

    def _addRequirement(self,requirement,primary):
        """Link the Deployment as being driven by the specified requirement,
        upgrading secondary status to primary if necessary"""

        if primary:
            self.primary_requirements[requirement.uid] = requirement
            if requirement.uid in self.secondary_requirements:
                del self.secondary_requirements[requirement.uid]
        elif requirement.uid not in self.primary_requirements:
            self.secondary_requirements[requirement.uid] = requirement

        self.component.requirements[requirement.uid] = requirement
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

    def _setHealthAndStatus(self):
        """Determines health of the deployment, based on own state and dependents."""
        # While we may be recursing set our own health to the native value
        self._health = self._possibleStates[self._status]

        #Now see if any dependent is worst than we are
        for dep_name in self.component.dependencies.keys():
            if dep_name in self.host.expected_deployments:
                dep_health = self.host.expected_deployments[dep_name].health
                if Health.worst([dep_health,self._health]) is not self._health:
                    self._health = Health.worst([dep_health,self._health])
                    self._status = "DependencyProblem"

    def functionalHealth(self):
        """Returns the functional health of the deployment, i.e. the worst of the component
        and the installation of the component"""
        if Health.worst([self.component.health, self.health]) is not self.health:
            return self.component.health
        else:
            return self.health

    def functionalStatus(self):
        """Returns the functional status of the deployment, i.e. the worst of the component
        and the installation of the component"""
        if Health.worst([self.component.health, self.health]) is not self.health:
            return "Component " + self.component.status
        else:
            return self.status

    def gatherStatus(self, installed_package_tuples, cm_working_root):
        """Determines current state of the deployment, assuming we running on the host"""
        if isinstance(self.component, RepoApplication):
            # For repo apps build a list of installed packages
            self.installed_packages = list(set(self.component.package) & set([t[0] for t in installed_package_tuples]))
            if len(self.installed_packages) == len(self.component.package):
                self._status = "Installed"
            elif len(self.installed_packages) == 0:
                self._status = "Missing"
            else:
                self._status = "PartiallyInstalled"
        elif isinstance(self.component, NonRepoApplication):
            # For non repo apps can only check existence of a path
            if hasattr(self.component,"install_location"):
                if os.path.exists(self.component.install_location):
                    self._status = "Installed"
                else:
                    self._status = "Missing"
            else:
                self._status = "Unknown"
                self.error = "No install_location to test for NonRepoApplication"
        elif isinstance(self.component, OtherFile):
            # For other files we can only check existence of a path
            if os.path.exists(os.path.join(self.component.directory,self.component.filename)):
                self._status = "Installed"
            else:
                self._status = "Missing"
        elif not self.component.default_repository:
            # For configured files outside the default repository we can only check existence of a path
            if os.path.exists(self.location):
                self._status = "Installed"
            else:
                self._status = "Missing"
        elif not hasattr(self,'location'):
            # Being a CM file without an expected deployment location is an error
            self._status = "Unknown"
            self.error = "No deployment path specified"
        else:
            # For CM based files check the relative state of the deployed file against the
            # up to date working copy of the repository
            cm_working_path = os.path.join(cm_working_root, self.component.cm_location, self.component.cm_filename)
            cmp = _ComparisonState(self.location,cm_working_path)

            if cmp.state == _ComparisonState.MATCH:                 self._status = "Installed"
            elif cmp.state == _ComparisonState.NO_LOCAL_FILE:       self._status = "Missing"
            elif cmp.state == _ComparisonState.LOCAL_FILE_NEWER:    self._status = "ModifiedLocally"
            elif cmp.state == _ComparisonState.MASTER_FILE_NEWER:   self._status = "OutOfDate"
            elif cmp.state == _ComparisonState.NO_MASTER_FILE:      self._status = "NotConfigured"
            else:
                self._status = "Unknown"
                self.error = "Neither local or CM copies found"


    def resetStatus(self):
        """Resets the current status to Unknown"""
        self._status = "Unknown"
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
            self._status = x_element.get('status')
            if x_element.get('error') is not None:
                self.error = x_element.get('error')
            if isinstance(self.component, RepoApplication):
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
