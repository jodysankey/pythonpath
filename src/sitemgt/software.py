#========================================================
# software.py
#========================================================
# $HeadURL:                                             $
# Last $Author: jody $
# $Revision: 742 $
# $Date: 2009-12-28 02:23:37 -0600 (Mon, 28 Dec 2009) $
#========================================================
# Classes to represent the software components within a
# site and their deployment onto hardware hosts
#========================================================



from .general import SiteObject

import os



class Language(SiteObject):
    """An interpreted language for scripting""" 

    def __init__(self, x_element):
        """Initialize the object"""      
        SiteObject.__init__(self,x_element,'language')
        self.application_names = []
        for x_app in x_element.findall('Application'):
            self.application_names.append(x_app.get('name'))



class Component(SiteObject):
    """An abstract software component of any type"""

    _expand_dicts = [['dependencies','deployments']]

    def __init__(self, x_element, type):
        """Initialize the object"""      
        # Set basic attributes 
        SiteObject.__init__(self,x_element,type)
        #Initially just store the dependent names; objects will be linked during linkComponentSet
        self.dependencies = {}
        for x_dep in x_element.findall('RequiredComponent'):
            self.dependencies[x_dep.get('name')] = None
        # Build a temp dictionary of expected deployment locations, and an empty real dictionary
        self.deployments = {}
        self._deployment_targets = {}
        for x_d in x_element.findall('Deployment'):
            path = os.path.join(x_d.get('directory'), self.cm_filename if x_d.get('filename') is None else x_d.get('filename'))
            self._deployment_targets[x_d.get('host_set')] = path

    def _classLink(self, siteDescription):
        """Initialize references to other component/language objects"""
        # Go through and set dependencies
        for dep_name in sorted(self.dependencies.keys()):
            self.dependencies[dep_name] = siteDescription.components[dep_name]

    def _crossLink(self, siteDescription):
        """Initialize references to other non-component objects"""
        # Ask the associated host_set to record each of the deployments we have a location for.
        # It will handle decomposing to all hosts in a group if necessary 
        for tgt in self._deployment_targets.keys():
            siteDescription.actors[tgt]._deployComponent(self,self._deployment_targets[tgt])



class RepoApplication(Component):
    """A software application (or set of applications) installed through an online repository system"""
    def __init__(self, x_element):
        """Initialize the object"""      
        Component.__init__(self, x_element, 'repoapplication')
        if x_element.find('Package') is not None:
            self.package = []
            for x_p in x_element.findall('Package'):
                self.package.append(x_p.get('name'))
        elif x_element.get('package') is not None:
            self.package = [x_element.get('package')]
        else:
            self.package = [self.name]




class NonRepoApplication(Component):
    """A software application not installed through an online repository system"""
    def __init__(self, x_element):
        """Initialize the object"""      
        Component.__init__(self, x_element, 'nonrepoapplication')





class CmComponent(Component):
    """A software component managed through a CM repository"""

    def __init__(self, x_element, type):
        """Initialize the object"""      
        # Set basic attributes including CM attributes to default if not explicit in the XML
        if x_element.get('cm_location') is not None and x_element.get('cm_filename') is None:
            self.cm_filename = x_element.get('name')
        Component.__init__(self,x_element,type)

    def _classLink(self, siteDescription):
        """Initialize references to other component/language objects"""
        Component._classLink(self, siteDescription)
        # Use the default repository if necessary 
        if hasattr(self,'cm_location') and not hasattr(self,'cm_repository'):
            self.cm_repository = siteDescription.default_cm_repository
            self.url = "svn://" + os.path.join(self.cm_repository,self.cm_location,self.cm_filename)




class Script(CmComponent):
    """An interpreted software script controlled through CM"""
    _expand_objects = [['language']]
    
    def __init__(self, x_element):
        """Initialize the object"""      
        CmComponent.__init__(self, x_element, 'script')
        # Note the language name here gets replaced by an object later (this is a bit sneaky)
        self.language = x_element.get('language')

    def _classLink(self, siteDescription):
        """Initialize references to other component/language objects"""
        CmComponent._classLink(self, siteDescription)
        # Now set language and any additional dependencies it incurs 
        self.language = siteDescription.languages[self.language]
        for app_name in self.language.application_names:
            self.dependencies[app_name] = siteDescription.components[app_name]




class ConfigFile(CmComponent):
    """An interpreted software script controlled through CM"""
    def __init__(self, x_element):
        """Initialize the object"""      
        CmComponent.__init__(self, x_element, 'configfile')
