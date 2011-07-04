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


from .general import SiteObject, Health, FAIL, DEGD, FAULT, UNKNOWN, OFF, GOOD

import sitemgt

import socket
import subprocess
import datetime
import tagwriter
import xml.etree.ElementTree


class Actor(SiteObject):
    """A high level site capability"""
    
    _expand_dicts = [['members', 'groups', 'responsibility_dict', 'requirement_dict', 'expected_deployments']]
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
                req = sitemgt.ActorRequirement(x_req, self)
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

    def isHostSet(self):
        """Returns true if this actor is a host or host group"""
        return isinstance(self, Host) or isinstance(self, HostGroup)

    def isGroup(self):
        """Returns true if this actor is a group or users or hosts"""
        return hasattr(self,'members')
        
    def _deployRequirement(self, requirement):
        """Document the deployment of all components needed by a requirement"""
        # More specific types of actor can override this with their own values
        pass

    def health(self):
        """Unless overridden the actor health is unmonitored"""
        if self._health is None: self._health = OFF
        return self._health

    
    
    
def _splitAptitudeLine(line):
    """Splits an aptitude output line into its package name and package description"""
    pos = line.find('- ')
    return [line[4:pos].strip(),line[pos+2:].strip().replace('"','')]


class Host(Actor):
    """A computer within the site"""

    def __init__(self, x_definition, x_functionality):
        """Initialize the object"""        
        Actor.__init__(self, x_definition, x_functionality, False, 'host')
        self.expected_deployments = {}

    def _deployRequiredComponent(self, component, requirement, primary):
        """Document the need for a component due to a requirement"""
        if component.name in self.expected_deployments.keys():
            # If this deployment is already linked to the host, just add the requirement
            self.expected_deployments[component.name]._addRequirement(requirement, primary)
        else:
            # Must create a new deployment
            depl = sitemgt.Deployment(self, component)
            depl._addRequirement(requirement, primary)
        # Now mark this same requirement as secondary for any components necessary to support this component
        for dep_component in component.dependencies.values():
            self._deployRequiredComponent(dep_component, requirement, False)

    def _deployRequirement(self, requirement):
        """Document the deployment of all components needed by a requirement"""
        for component in requirement.primary_components.values():
            # Any component directly related to a requirement is primary
            self._deployRequiredComponent(component, requirement, True)
    
    def _deployComponent(self, component, location):
        """Document the deployment of a component to a location"""
        if component.name in self.expected_deployments.keys():
            # If this deployment is already linked to the host, just set the location
            self.expected_deployments[component.name].location = location
        else:
            # Must create a new deployment (it will link itself to us)
            sitemgt.Deployment(self, component, location)
    

    def gatherDeploymentStatus(self, cm_working_root):
        """Determine the current state of all deployments on this host"""
        #This function only works if we *ARE* the host
        if self.name.lower() != socket.gethostname().lower():
            raise Exception("Can only gather deployments for current host ({}), not {}".format(socket.gethostname(), self.name))
        
        self.resetDeploymentStatus();
        
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
            depl.gatherStatus(installed_packages, cm_working_root)

        self.status_date = datetime.datetime.today()


    def saveDeploymentStatus(self, filename):
        """Dumps the current component deployment status using an XML tag writer object on the specified file"""
        tag_writer = tagwriter.TagWriter(filename)
        tag_writer.open('DeploymentStatus')
        tag_writer.open('Host','name="{}" date="{}"'.format(self.name, self.status_date.strftime("%Y-%m-%d %H:%M")))

        for depl in self.expected_deployments.values():
            depl.saveStatus(tag_writer)            
        for pkg in self.upgradable_packages:
            tag_writer.write('Upgradable','name="{}" description="{}"'.format(pkg[0],pkg[1]))
        for pkg in self.unexpected_packages:
            tag_writer.write('Unexpected','name="{}" description="{}"'.format(pkg[0],pkg[1]))

        tag_writer.close(2)


    def resetDeploymentStatus(self):      
        """Clears all existing component deployment information"""
        self.resetHealth()
        if hasattr(self,'status'): 
            delattr(self,'status')
        if hasattr(self,'status_date'): 
            delattr(self,'status_date')
        if hasattr(self,'upgradable_packages'): 
            delattr(self,'upgradable_packages')
        if hasattr(self,'unexpected_packages'): 
            delattr(self,'unexpected_packages')
        for depl in self.expected_deployments.values():
            depl.resetStatus()            

        
    def loadDeploymentStatus(self, filename):      
        """Load the component deployment status from the named file, using an XML ElementTree"""

        self.resetDeploymentStatus()
        
        # Find root element and check it is for the correct host
        book = xml.etree.ElementTree.parse(filename).getroot()
        x_host = book.find('Host')
        if x_host.get('name') == self.name:
            self.status_date = datetime.datetime.strptime(x_host.get('date'), "%Y-%m-%d %H:%M")
            
            for x_d in x_host.findall('Deployment'):
                if x_d.get('name') in self.expected_deployments.keys():
                    self.expected_deployments[x_d.get('name')].loadStatus(x_d)

            self.upgradable_packages = [(p.get('name'),p.get('description')) for p in x_host.findall('Upgradable')]
            self.unexpected_packages = [(p.get('name'),p.get('description')) for p in x_host.findall('Unexpected')]
 
 
    def health(self):
        """Determines health of the host, based on state of its software deployments.
        Note this function sets status"""

        if self._health is None:
            # Typically our state is based only on the deployments
            if len(self.expected_deployments) == 0:
                self._health = GOOD
                self.status = "NoDeployments"
            else:
                self._health = Health.amortized([d.health() for d in self.expected_deployments.values()])
                if self._health is UNKNOWN:
                    self.status = "UnknownDeploymentState"
                elif self._health is OFF: #Dont see how this could happen
                    self.status = "UnmonitoredDeployments"
                elif self._health in [FAIL, DEGD, FAULT]:
                    self.status = "DeploymentProblem"
                else:
                    self.status = "Good"

            # But if they look ok, check our off nominal packages
            if self._health is GOOD:
                if hasattr(self,'upgradable_packages') and len(self.upgradable_packages)>0:
                    self.status = "PackagesNeedUpgrade"
                    self._health = FAULT
                elif hasattr(self,'unexpected_packages') and len(self.unexpected_packages)>0:
                    self.status = "UnexpectedPackages"
                    self._health = GOOD
        return self._health

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

