#========================================================
# actors.py
#========================================================
# $HeadURL:                                             $
# Last $Author: jody $
# $Revision: 742 $
# $Date: 2009-12-28 02:23:37 -0600 (Mon, 28 Dec 2009) $
#========================================================
# Classes to represent the actors within a site, both  
# computers (Hosts) and Users, and the deployment of 
# software components onto Hosts
#========================================================


from .general import SiteObject
from .functionality import ActorRequirement
from .deployment import Deployment

import socket
import subprocess


class Actor(SiteObject):
    """A high level site capability"""
    
    _expand_dicts = [['members', 'groups', 'responsibilities', 'requirements', 'expected_deployments']]
    _expand_objects = []

    def __init__(self, x_definition, x_functionality, is_group, type):
        """Initialize the object"""        
        # Set basic attributes
        SiteObject.__init__(self, x_definition, type)
        
        # Mark dictionaries with blanks until link attaches them
        self.responsibilities = {}
        if is_group:
            self.members = {}
            for x_m in x_definition.findall('Member'):
                self.members[x_m.get('name')] = None
        else:
            self.groups = {}
            
        self.requirements = {}
        if x_functionality is not None:
            for x_req in x_functionality.findall('*'):
                req = ActorRequirement(x_req, self)
                self.requirements[req.uid] = req

    def _classLink(self, siteDescription):
        """Initialize references to other actor objects"""
        
        # Define actor group membership
        if hasattr(self, 'members'):
            for member_name in sorted(self.members.keys()):
                member = siteDescription.actors[member_name]
                self.members[member_name] = member
                member.groups[self.name] = self
        
    def _crossLink(self, siteDescription):
        """Initialize references to other non-actor objects"""
        
        # Ask requirements to link their components, and deploy these requirements
        for req in self.requirements.values():
            req._crossLink(siteDescription)
            self._deployRequirement(req)

        
    def _deployRequirement(self, requirement):
        """Document the deployment of all components needed by a requirement"""
        # More specific types of actor can override this with their own values
        pass
    
    
    
def _splitAptitudeLine(line):
    """Splits an aptitude output line into its package name and package description"""
    pos = line.find('- ')
    return [line[4:pos].strip(),line[pos+2:].strip()]


class Host(Actor):
    """A computer within the site"""

    def __init__(self, x_definition, x_functionality):
        """Initialize the object"""        
        Actor.__init__(self, x_definition, x_functionality, False, 'host')
        self.expected_deployments = {}

    def _deployRequirement(self, requirement):
        """Document the deployment of all components needed by a requirement"""
        for component in requirement.components.values():
            if component.name in self.expected_deployments.keys():
                # If this deployment is already linked to the host, just add the requirement
                self.expected_deployments[component.name]._addRequirement(requirement)
            else:
                # Must create a new deployment
                depl = Deployment(self, component)
                depl._addRequirement(requirement)
    
    def _deployComponent(self, component, location):
        """Document the deployment of a component to a location"""
        if component.name in self.expected_deployments.keys():
            # If this deployment is already linked to the host, just set the location
            self.expected_deployments[component.name].location = location
        else:
            # Must create a new deployment (it will link itself to us)
            Deployment(self, component, location)
    

    
    def gatherDeployments(self):
        """Determine the current state of all deployments on this host"""
        #This function only works if we *ARE* the host
        if self.name.lower() != socket.gethostname().lower():
            raise Exception("Can only gather deployments for current host ({}), not {}".format(socket.gethostname(), self.name))
        
        #Build a list unexpected packages (i.e. installed, orphan, but not expected)
        expected_packages = []
        for package_set in [depl.component.package for depl in self.expected_deployments.values() if hasattr(depl.component,'package')]:
            expected_packages.extend(package_set)

        raw_orphaned = subprocess.check_output(['debfoster','-ns']).decode('utf-8')
        orphaned_packages = raw_orphaned[raw_orphaned.find('\n')+1:].split()
        raw_installed = subprocess.check_output(['aptitude','search','~i']).decode('utf-8')[:-1]
        installed_packages = [_splitAptitudeLine(ln) for ln in raw_installed.split('\n')]
        self.unexpected_packages = []
    
        for tuple in installed_packages:
            if tuple[0] in orphaned_packages and tuple[0] not in expected_packages:
                self.unexpected_packages.append(tuple)

        # Build a set of upgradable packages 
        raw_upgradable = subprocess.check_output(['aptitude','search','~U']).decode('utf-8')
        self.upgradable_packages = [_splitAptitudeLine(ln) for ln in raw_upgradable.split('\n')[:-1]]
     
        #Ask each expected deployment to deal with itself, providing the installed_set for speed
        for depl in self.expected_deployments.values():
            depl.gatherState(installed_packages)


class HostGroup(Actor):
    """A collections of computers within the site"""
    def __init__(self, x_definition, x_functionality):
        """Initialize the object"""        
        Actor.__init__(self, x_definition, x_functionality, True, 'hostgroup')
    def _deployRequirement(self, requirement):
        """Document the deployment of all components needed by a requirement to our members"""
        for member in self.members.values():
            member._deployRequirement(requirement)
    def _deployComponent(self, component, location):
        """Document the deployment of a component to a location to our members"""
        for member in self.members.values():
            member._deployComponent(component, location)


class User(Actor):
    """A user of the site"""
    def __init__(self, x_definition, x_functionality):
        """Initialize the object"""        
        Actor.__init__(self, x_definition, x_functionality, False, 'user')


class UserGroup(Actor):
    """A collection of users of the site"""
    def __init__(self, x_definition, x_functionality):
        """Initialize the object"""        
        Actor.__init__(self, x_definition, x_functionality, True, 'usergroup')

