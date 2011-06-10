#========================================================
# functionality.py
#========================================================
# $HeadURL:                                             $
# Last $Author: jody $
# $Revision: 742 $
# $Date: 2009-12-28 02:23:37 -0600 (Mon, 28 Dec 2009) $
#========================================================
# Classes to represent the functionality of a site;  
# level level Capabilities, SystemRequirements, and 
# ActorRequirements
#========================================================


from .general import SiteObject, Health, OFF, UNKNOWN, GOOD, FAULT, DEGD, FAIL
#import xml.etree.ElementTree

import sitemgt



class SystemRequirement(SiteObject):
    """A requirement to be met by the entire system"""

    _expand_dicts = [['actor_requirements'],['actor_requirements']]
    _expand_objects = [['capability']]
    _importance_dict = {'5':'Critical', '4':'High', '3':'Medium', '2':'Low', '1':'Minimal'}

    def __init__(self, x_element, capability):
        """Initialize the object"""
        SiteObject.__init__(self,x_element,'systemrequirement')
        self.text = self.text.replace("%","The System")
        self.capability = capability
        self.name = self.uid
        self.importance_text = self._importance_dict[self.importance]

        # Mark dictionary with blanks until link attaches them
        self.actor_requirements = {}
        for x_ar in x_element.findall('Requirement'):
            self.actor_requirements[x_ar.get('uid')] = None

    def _crossLink(self, siteDescription):
        """Initialize references to other objects within the site description"""
        for ar_uid in sorted(self.actor_requirements.keys()):
            ar = siteDescription.actor_requirements[ar_uid]
            self.actor_requirements[ar_uid] = ar
            ar.system_requirements[self.uid] = self

    def hostSets(self):
        """Return an set of supporting hosts and host groups"""
        return set([ar.actor for ar in self.actor_requirements.values() if ar.actor.isHostSet()])
            
    def hosts(self):
        """Return an set of supporting hosts, with groups expanded"""
        host_sets = self.hostSets()
        hosts = set()
        for act in host_sets:
            if act.isGroup():   hosts.update(act.members.values())
            else:               hosts.add(act)
        return hosts
                    
    def userSets(self):
        """Return an set of supporting users and user groups"""
        return set([ar.actor for ar in self.actor_requirements.values() if not ar.actor.isHostSet()])

    def users(self):
        """Return an set of supporting users, with groups expanded"""
        user_sets = self.userSets()
        users = set()
        for act in user_sets:
            if act.isGroup():   users.update(act.members.values())
            else:               users.add(act)
        return users

    def htmlName(self):
        """Overridden to include a target within the capability page"""
        return self.capability.htmlName() + "#" + self.uid

    def health(self):
        """Determines health of the system requirement, based on health of its actor requirements"""
        if self._health is None:
            # In general, system requirement health will be based on testing, which is not yet implemented 
            self._health = OFF
            self.status = "TestingNotImplemented"
        return self._health



class ActorRequirement(SiteObject):
    """A requirement to be met by a particular actor in the system"""

    _expand_dicts = [['system_requirements','components'],['system_requirements','components']]
    _expand_objects = [['actor']]

    
    def __init__(self, x_element, actor):
        """Initialize the object"""
        SiteObject.__init__(self,x_element,'actorrequirement')
        self.text = self.text.replace("%",actor.name)
        self.actor = actor
        self.name = self.uid

        # Mark dictionary with blanks until link attaches them
        self.system_requirements = {}
        self.components = {}
        self.deployments = {}
        for x_cmp in x_element.findall('Component'):
            self.components[x_cmp.get('name')] = None

    def _crossLink(self, siteDescription):
        """Initialize references to other objects within the site description"""
        for cmp_name in sorted(self.components.keys()):
            cmp = siteDescription.components[cmp_name]
            self.components[cmp_name] = cmp
    
    def health(self):
        """Determines health of the actor requirement, based on health of its associated deployments"""
        if self._health is None:
            if not self.actor.isHostSet():
                # User based requirements cannot be monitored
                self._health = OFF
                self.status = "UserBased"
            elif len(self.deployments)==0:
                # Requirements with no software cannot be monitored
                self._health = OFF
                self.status = "NoDeployments"
            else:
                self._health = Health.amortized([d.functionalHealth() for d in self.deployments.values()])
                self.status = "Deployments {}".format(self._health)
        return self._health

    

class ActorResponsibility(SiteObject):
    """A partitioning of functionality to an actor set in support of a site capability"""
    
    _expand_objects = [['capability','actor']]
    
    def __init__(self, x_element, capability):
        """Initialize the object"""
        if x_element.tag == 'UserResponsibility':
            SiteObject.__init__(self,x_element,'userresponsibility')
            self.description = self.description.replace("%",self.user_set)
        else:
            SiteObject.__init__(self,x_element,'hostresponsibility')
            self.description = self.description.replace("%",self.host_set)
        self.capability = capability
        
    def _crossLink(self, siteDescription):
        """Initialize references to other objects within the site description"""
        self.actor = siteDescription.actors[self.user_set if hasattr(self,'user_set') else self.host_set]
        self.actor.responsibilities[self.capability.name] = self
        

class Capability(SiteObject):
    """A high level site capability"""
    
    _expand_dicts = [['responsibilities','requirements']]
    _translation = {
            '5':{UNKNOWN:UNKNOWN, OFF:OFF, GOOD:GOOD, FAULT:DEGD, DEGD:FAIL, FAIL:FAIL},
            '4':{UNKNOWN:UNKNOWN, OFF:OFF, GOOD:GOOD, FAULT:FAULT, DEGD:DEGD, FAIL:FAIL},
            '3':{UNKNOWN:UNKNOWN, OFF:OFF, GOOD:GOOD, FAULT:FAULT, DEGD:DEGD, FAIL:DEGD},
            '2':{UNKNOWN:UNKNOWN, OFF:OFF, GOOD:GOOD, FAULT:FAULT, DEGD:FAULT, FAIL:FAULT},
            '1':{UNKNOWN:UNKNOWN, OFF:OFF, GOOD:GOOD, FAULT:FAULT, DEGD:FAULT, FAIL:FAULT},
                    }

    def __init__(self, x_element):
        """Initialize the object"""        
        # Set basic attributes
        SiteObject.__init__(self,x_element,'capability')
        # Populate a dictionary of all child requirements        
        self.requirements = {}
        for x_sr in x_element.findall('SystemRequirement'):
            sr = SystemRequirement(x_sr, self)
            self.requirements[sr.uid] = sr
        # Populate a dictionary of all child responsibilities        
        self.responsibilities = {}
        #for x_rsp in x_element.findall('UserResponsibility|HostResponsibility'):
        for x_rsp in x_element.findall('UserResponsibility'):
            rsp = ActorResponsibility(x_rsp, self)
            self.responsibilities[rsp.user_set] = rsp
        for x_rsp in x_element.findall('HostResponsibility'):
            rsp = ActorResponsibility(x_rsp, self)
            self.responsibilities[rsp.host_set] = rsp
            
    def _crossLink(self, siteDescription):
        """Initialize references to other non capability objects"""
        for req in self.requirements.values():
            req._crossLink(siteDescription)
        for resp in self.responsibilities.values():
            resp._crossLink(siteDescription)
            
    def health(self):
        """Determines health of the system requirement, based on health of its actor requirements"""
        if self._health is None:
            self._health = Health.worst([self._translation[sr.importance][sr.health()] for sr in self.requirements.values()])
            self.status = self._health.name
        return self._health


