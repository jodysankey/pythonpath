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



from .general import SiteObject, GOOD, DEGD, FAIL, FAULT, OFF

import os



class Language(SiteObject):
    """An interpreted language for scripting""" 

    def __init__(self, x_element):
        """Initialize the object"""      
        SiteObject.__init__(self,x_element,'language')
        self.application_names = []
        for x_app in x_element.findall('Application'):
            self.application_names.append(x_app.get('name'))

    def __str__(self):
        return self.name


class Component(SiteObject):
    """An abstract software component of any type"""

    _expand_dicts = [['dependencies','deployments']]

    def __init__(self, x_element, type):
        """Initialize the object"""      
        # Set basic attributes 
        SiteObject.__init__(self,x_element,type)
        #Initially just store the dependent and relation names; objects will be linked during linkComponentSet
        self.dependencies = {}
        for x_dep in x_element.findall('RequiredComponent'):
            self.dependencies[x_dep.get('name')] = None
        self.relations = {}
        for x_dep in x_element.findall('RelatedComponent'):
            self.relations[x_dep.get('name')] = None
        # Build a temp dictionary of expected deployment locations, and an empty real dictionary
        self.deployments = {}
        self._deployment_targets = {}
        self.requirements = {}
        self.dependers = {}
        for x_d in x_element.findall('Deployment'):
            path = os.path.join(x_d.get('directory'), self.cm_filename if x_d.get('filename') is None else x_d.get('filename'))
            self._deployment_targets[x_d.get('host_set')] = path

    def _classLink(self, siteDescription):
        """Initialize references to other component/language objects"""
        # Go through and set dependencies and relationships
        for dep_name in sorted(self.dependencies.keys()):
            self._registerDependency(siteDescription.components[dep_name])
        for rel_name in sorted(self.relations.keys()):
            self.relations[rel_name] = siteDescription.components[rel_name]

    def _crossLink(self, siteDescription):
        """Initialize references to other non-component objects"""
        # Ask the associated host_set to record each of the deployments we have a location for.
        # It will handle decomposing to all hosts in a group if necessary 
        for tgt in self._deployment_targets.keys():
            siteDescription.actors[tgt]._deployComponent(self,self._deployment_targets[tgt])

    def _registerDependency(self, depended_component):
        """Adds a bidirectionaly dependency link from self to depended_component"""
        self.dependencies[depended_component.name] = depended_component
        depended_component.dependers[self.name] = self

    def health(self):
        """Unless overridden the component health is unmonitored"""
        if self._health is None: self._health = OFF
        return self._health



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




class OtherFile(Component):
    """A miscellaneous file not managed through site CM"""
    def __init__(self, x_element):
        """Initialize the object"""      
        Component.__init__(self,x_element,'otherfile')
        if x_element.get('status') is None:     self.status = 'Working'
        if x_element.get('filename') is None:   self.filename = x_element.get('name')

    _possibleStates = {'Working':GOOD, 'Suspect':FAULT, 'Defective':DEGD}

    def health(self):
        if self._health is None: self._health = self._possibleStates[self.status]
        return self._health



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
        # If we dont have our own repository, use the default
        if not hasattr(self,'cm_repository'):
            self.cm_repository = siteDescription.default_repository
        self.default_repository = (self.cm_repository == siteDescription.default_repository)

    def url(self):
        #Returns a url for the subversion repository
        return os.path.join('svn://'+self.cm_repository, self.cm_location, self.cm_filename)


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
            self._registerDependency(siteDescription.components[app_name])

    _possibleStates = {'NotStarted':FAIL, 'NotFinished':DEGD, 'Working':GOOD,
                       'Suspect':FAULT, 'Defective':DEGD, 'Dead': FAIL }

    def health(self):
        if self._health is None: self._health = self._possibleStates[self.status]
        return self._health




class ConfigFile(CmComponent):
    """An interpreted software script controlled through CM"""
    def __init__(self, x_element):
        """Initialize the object"""      
        CmComponent.__init__(self, x_element, 'configfile')
        
    _possibleStates = {'Working':GOOD, 'Suspect':FAULT, 'Defective':DEGD }

    def health(self):
        if self._health is None: self._health = self._possibleStates[self.status]
        return self._health

