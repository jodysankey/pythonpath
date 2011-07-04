#========================================================
# SiteDescription.py
#========================================================
# $HeadURL:                                             $
# Last $Author: jody $
# $Revision: 742 $
# $Date: 2009-12-28 02:23:37 -0600 (Mon, 28 Dec 2009) $
#========================================================
# SiteDescription class to parse standard format XML 
# file and create a matching Python representation, based
# mainly on classes derived from SiteObject 
#========================================================

#Imports
import xml.etree.ElementTree
import os

#from .siteobject import SiteObject
from .functionality import Capability
from .actors import User, Host, UserGroup, HostGroup
from .software import Script, RepoApplication, NonRepoApplication, ConfigFile, OtherFile, Language

__author__="Jody"
__date__ ="$Date:$"


def mergeDictionaries(dicts):
    out = {}
    for dict in dicts:
        out.update(dict)
    return out

def makeObjectDictionary(class_type, x_elements):
    out = {}
    for x_el in x_elements:
        out[x_el.get('name')] = class_type(x_el)
    return out

def makeObjectList(class_type, x_elements):
    out = []
    for x_el in x_elements:
        out.append(class_type(x_el))
    return out

def makeActorDictionary(class_type, x_elements, supplements):
    out = {}
    for x_el in x_elements:
        out[x_el.get('name')] = class_type(x_el, supplements[x_el.get('name')])
    return out


class SiteDescription(object):
    """A class to parse and represent a SiteDescription file"""

    def __init__(self,filename):
        """Initialize the site description object, building dictionaries for each type of information"""
        self.filename = filename
        
        # Find XML root elements for each key type of information
        tree = xml.etree.ElementTree.parse(filename)
        book = tree.getroot()
        x_actors = book.find('Actors')
        x_func = book.find('Functionality')
        x_languages = book.find('Software').find('ScriptingLanguages')
        x_components = book.find('Software').find('Components')

        self.default_repository = x_components.get('default_repository')

        # Note the order in which different object types are linked is important
        # since there are a (small number) of assumptions about what exists first 

        #Prebuild a dictionary of functional references for every actor
        actor_x_funcs = {}
        for x_ad in x_actors.findall('*'):
            actor_x_funcs[x_ad.get('name')] = None
        for x_af in x_func.findall('*'):
            actor_x_funcs[x_af.get('name')] = x_af

        # Build each different type of actor, passing pointers to both XML elements which define it
        self.users = makeActorDictionary(User, x_actors.findall('User'), actor_x_funcs)
        self.user_groups = makeActorDictionary(UserGroup, x_actors.findall('UserGroup'), actor_x_funcs)
        self.hosts = makeActorDictionary(Host, x_actors.findall('Host'), actor_x_funcs)
        self.host_groups = makeActorDictionary(HostGroup, x_actors.findall('HostGroup'), actor_x_funcs)
        # Assemble dictionary of all actors  
        self.actors = mergeDictionaries([self.users, self.user_groups, self.hosts, self.host_groups])

        # Assemble dictionary of all actors requirement_dict and link actors to each other
        self.actor_requirement_dict = {}
        for actor in self.actors.values():
            self.actor_requirement_dict.update(actor.requirements)
            actor._classLink(self)


        # Assemble dictionaries of all software component types
        self.languages = makeObjectDictionary(Language,x_languages.findall('*'))    

        self.applications = makeObjectDictionary(RepoApplication,x_components.findall('RepoApplication'))    
        self.applications.update(makeObjectDictionary(RepoApplication,x_components.findall('RepoApplicationSet')))   
        self.applications.update(makeObjectDictionary(NonRepoApplication,x_components.findall('NonRepoApplication')))   
        self.scripts =      makeObjectDictionary(Script,x_components.findall('Script'))    
        self.config_files = makeObjectDictionary(ConfigFile,x_components.findall('ConfigurationFile'))
        self.other_files =  makeObjectDictionary(OtherFile,x_components.findall('OtherFile'))
        self.components =   mergeDictionaries([self.applications, self.scripts, self.config_files, self.other_files])

        # Create then link capabilities
        self.capabilities = makeObjectList(Capability,x_func.findall('Capability'))
        for cap in self.capabilities:
            cap._crossLink(self)

        # Link components to each other and other objects
        for cpt in self.components.values():
            cpt._classLink(self)
            cpt._crossLink(self)

        # Link actors to other objects
        for actor in self.actors.values():
            actor._crossLink(self)
        
    def loadDeploymentStatus(self, filename_format):
        """Loads deployment files for every host with a file matching filename_format"""
        for host in self.hosts.values():
            host.resetDeploymentStatus()
            if os.path.exists(filename_format.format(host.name)):
                host.loadDeploymentStatus(filename_format.format(host.name))

    def __str__(self):
        """Return a string representation"""
        output = 'CAPABILITIES:\n============\n'
        for cap_name in sorted(self.capabilities.keys()):
            output += str(self.capabilities[cap_name]) + '\n'
        output += '\nACTORS:\n======\n'
        for actor_name in sorted(self.actors.keys()):
            output += str(self.actors[actor_name]) + '\n'
        output += '\nLANGUAGES:\n==========\n'
        for lang_name in sorted(self.languages.keys()):
            output += str(self.languages[lang_name]) + '\n'
        output += '\nCOMPONENTS:\n==========\n'
        for cpt_name in sorted(self.components.keys()):
            output += str(self.components[cpt_name]) + '\n'
        return output



if __name__ == '__main__':
    # Test Script
    sd = SiteDescription("/home/jody/files/computing/requirement_dict/SiteDescription.xml")

    
    
