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


from .general import SiteObject
#import xml.etree.ElementTree


_importance_dict = {'5':'Critical', '4':'High', '3':'Medium', '2':'Low', '1':'Minimal'}


class SystemRequirement(SiteObject):
    """A requirement to be met by the entire system"""

    _expand_dicts = [['actor_requirements'],['actor_requirements']]
    _expand_objects = [['capability']]
    
    def __init__(self, x_element, capability):
        """Initialize the object"""
        SiteObject.__init__(self,x_element,'systemrequirement')
        self.text = self.text.replace("%","The System")
        self.capability = capability
        self.name = self.uid
        self.importance_text = _importance_dict[self.importance]

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
        for x_cmp in x_element.findall('Component'):
            self.components[x_cmp.get('name')] = None

    def _crossLink(self, siteDescription):
        """Initialize references to other objects within the site description"""
        for cmp_name in sorted(self.components.keys()):
            cmp = siteDescription.components[cmp_name]
            self.components[cmp_name] = cmp


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
        for x_rsp in x_element.findall('UserResponsibility|HostResponsibility'):
            rsp = ActorResponsibility(x_rsp, self)
            self.responsibilities[rsp.user_set] = rsp
            
    def _crossLink(self, siteDescription):
        """Initialize references to other non capability objects"""
        for req in self.requirements.values():
            req._crossLink(siteDescription)
        for resp in self.responsibilities.values():
            resp._crossLink(siteDescription)
            


