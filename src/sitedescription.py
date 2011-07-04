##========================================================
## sitedescription.py
##========================================================
## $HeadURL:                                             $
## Last $Author: jody $
## $Revision: 742 $
## $Date: 2009-12-28 02:23:37 -0600 (Mon, 28 Dec 2009) $
##========================================================
## SiteDescription class to parse standard format XML 
## file and create a matching Python representation
##========================================================
#
##Imports
#import xml.etree.ElementTree
#import os
#
#__author__="Jody"
#__date__ ="$Date:$"
#
#
#importance_dict = {'5':'Critical', '4':'High', '3':'Medium', '2':'Low', '1':'Minimal'}
#
#
#class SiteObject(object):
#    """A simple class derived from an XML element"""
#    
#    def __init__(self,x_element):
#        """Initialize all XML attributes as properties"""
#        for (a_name, a_value) in x_element.items():
#            self.__dict__[a_name] = a_value
#    def __str__(self):
#        """Return a string representation"""
#        attribs = ", ".join([x+':'+str(self.__dict__[x]) for x in self.__dict__.keys() if x!='name'])
#        return "[{} <{}>]".format(self.name, attribs)
#    
#    def htmlName(self):
#        """Return the file name to be used for an associated html"""
#        return self.type.lower().replace(' ','_') + "_" + self.name.replace(' ','_') + ".html"
#
#
#class Deployment(object):
#    """A simple class to represent a deployment of a component onto a host, initialized either
#    manually (if inferred from a requirement), or from an XML object (if explicit in XML)
#    
#    This inference and the fact that deployments are triple linked to components, hosts and
#    requirements makes it worth defining as its own class"""
#
#    def __init__(self, host, component):
#        """Initialize linkages"""
#        self.requirements = {}
#        self.host = host
#        host.expected_deployments[component.name] = self
#        self.component = component
#        component.deployments[host.name] = self
#        
#    def setToXml(self,x_element):
#        """Initialize specific XML attributes as properties"""
#        if x_element.get('directory') is not None: 
#            self.directory = x_element.get('directory')
#            if x_element.get('filename') is not None: 
#                self.filename = x_element.get('filename')
#            else:
#                self.filename = self.component.cm_filename 
#    
#    def addRequirement(self,requirement):
#        """Link the Deployment as being driven by the specified requirement"""
#        self.requirements[requirement.uid] = requirement
#        requirement.components[self.component.name] = self.component
#    
#    def __str__(self):
#        """Return a string representation"""
#        attribs = ", ".join([x+':'+self.__dict__[x] for x in self.__dict__.keys() if x!='name'])
#        return "![{} <{}>]!".format(self.name, attribs)
#
#    def hasLocation(self):
#        """Returns true if the deployment contains a meaningful location""" 
#        return hasattr(self, 'directory') or hasattr(self.component, 'installLocation')
#
#    def location(self):
#        """Returns a string assessment of the deployment location""" 
#        if hasattr(self, 'directory'):
#            return os.path.join(self.directory,self.filename)
#        elif hasattr(self.component, 'installLocation'):
#            return self.component.installLocation
#        elif hasattr(self.component, 'package'): 
#            return 'Via Repository'
#        else:
#            return 'Unknown'
#
#
#
##class Host(SiteObject):
##    def typename(self): return "host"
##
##class HostGroup(SiteObject):
##    def typename(self): return "hostgroup"
##
##class User(SiteObject):
##    def typename(self): return "user"
##
##class UserGroup(SiteObject):
##    def typename(self): return "usergroup"
##
##class Capability(SiteObject):
##    def typename(self): return "capability"
##
##class SystemReq(SiteObject):
##    def typename(self): return "sysreq"
##    
##class HostReq(SiteObject):
##    def typename(self): return "hostreq"
##
##class UserReq(SiteObject):
##    def typename(self): return "userreq"
##
##class Responsibility(SiteObject):
##    def typename(self): return "responsibility"
#
#
#
#    
#class SiteDescription(object):
#    """A class to parse and represent a SiteDescription file"""
#
#    def __init__(self,filename):
#        self.filename = filename
#        tree = xml.etree.ElementTree.parse(filename)
#        book = tree.getroot()
#        
#        # Find root elements for each key type of information
#        x_actors = book.find('Actors')
#        x_func = book.find('Functionality')
#        x_languages = book.find('Software').find('ScriptingLanguages')
#        x_components = book.find('Software').find('Components')
#
#        # Build dictionaries for each type of information using specific helper functions
#        # Assemble higher level aggregates from these specific dictionaries        
#
#        #Note order is important here, since some build functions assume other objects already exist
#        self.requirements = {}
#        self.users = self.__buildActorSet(x_actors.findall('User'),x_func,'user',None)
#        self.userGroups = self.__buildActorSet(x_actors.findall('UserGroup'),x_func,'usergroup',self.users)
#        self.hosts = self.__buildActorSet(x_actors.findall('Host'),x_func,'host',None)
#        self.hostGroups = self.__buildActorSet(x_actors.findall('HostGroup'),x_func,'hostgroup',self.hosts)
#        self.actors = {}
#        self.actors.update(self.users)
#        self.actors.update(self.userGroups)
#        self.actors.update(self.hosts)
#        self.actors.update(self.hostGroups)
#
#        self.applications = {}
#        self.applications.update(self.__buildComponentSet(x_components,x_languages,"RepoApplication"))
#        self.applications.update(self.__buildComponentSet(x_components,x_languages,"NonRepoApplication"))
#        self.default_cm_repository = x_components.get('default_cm_repository')
#        self.scripts = self.__buildComponentSet(x_components,x_languages,"Script")
#        self.configFiles = self.__buildComponentSet(x_components,x_languages,"ConfigurationFile")        
#        self.components = {}
#        self.components.update(self.applications)
#        self.components.update(self.scripts)
#        self.components.update(self.configFiles)
#
#        self.capabilities = self.__buildCapabilitySet(x_func)
#
#        self.__linkComponentSet(self.components)
#        self.__linkActorSet(self.hosts)
#        self.__linkActorSet(self.hostGroups)
#
#
#    def __str__(self):
#        """Return a string representation"""
#        output = 'Actors:\n'
#        for actor_name in sorted(self.actors.keys()):
#            output += str(self.actors[actor_name]) + '\n'
#        return output
#
#
#
#    def __buildCapabilitySet(self,x_func):
#        # Create a dictionary of all capabilities, given the XML functionality element
#        ret = {}
#        for x_el in x_func.findall('Capability'):
#            cap = SiteObject(x_el)
#            cap.type = 'capability'
#            cap.requirements = {}
#            cap.responsibilities = {}
#
#            for x_sr in x_el.findall('SystemRequirement'):
#                sr = SiteObject(x_sr)
#                sr.text = sr.text.replace("%","The System")
#                sr.importance_text = importance_dict[sr.importance]
#                sr.actor_requirements = {}
#                sr.capability = cap
#                for x_ar in x_sr.findall('Requirement'):
#                    ar = self.requirements[x_ar.get('uid')]
#                    sr.actor_requirements[ar.uid] = ar
#                    ar.system_requirements[sr.uid] = sr
#                cap.requirements[sr.uid] = sr
#
#            for x_rsp in x_el.findall('UserResponsibility'):
#                rsp = SiteObject(x_rsp)
#                rsp.actor = self.actors[rsp.user_set]
#                rsp.description = rsp.description.replace("%",rsp.user_set)
#                rsp.capability = cap
#                rsp.actor.responsibilities[cap.name] = rsp
#                cap.responsibilities[rsp.actor.name] = rsp
#            for x_rsp in x_el.findall('HostResponsibility'):
#                rsp = SiteObject(x_rsp)
#                rsp.actor = self.actors[rsp.host_set]
#                rsp.description = rsp.description.replace("%",rsp.host_set)
#                rsp.capability = cap
#                rsp.actor.responsibilities[cap.name] = rsp
#                cap.responsibilities[rsp.actor.name] = rsp
#
#            ret[cap.name] = cap
#
#        return ret
#
#
#    def __buildActorSet(self,x_actors,x_func,type_name,possible_members):
#        # Create a dictionary of all actors of the specified type, given the XML actors element
#        ret = {}
#        for x_el in x_actors:
#            ob = SiteObject(x_el)
#            ob.type = type_name
#            ob.responsibilities = {}
#            
#            #Add a dictionary of either containing groups or contained members
#            if possible_members is None:
#                ob.groups = {}
#            else:
#                ob.members = {}
#                for x_m in x_el.findall('Member'):
#                    mem_name = x_m.get('name')
#                    ob.members[mem_name] = possible_members[mem_name]
#                    possible_members[mem_name].groups[ob.name] = ob
#            
#            # Add a dictionary of actor requirements, holding any required component names in
#            # temporary dictionaries until later when the objects will be available 
#            ob.requirements = {}
#            ob.expected_deployments = {}
#            for x_reqs in x_func.findall('*'):
#                if x_reqs.get('name') == ob.name:
#                    for x_req in x_reqs.findall('*'):
#                        req = SiteObject(x_req)
#                        req.text = req.text.replace("%",ob.name)
#                        req.actor = ob
#                        req.system_requirements = {}
#                        req.components = {}
#                        for x_cmp in x_req.findall('Component'):
#                            req.components[x_cmp.get('name')] = None
#                        ob.requirements[req.uid] = req
#                        self.requirements[req.uid] = req
#            ret[ob.name] = ob
#        return ret
#        
#    def __linkActorSet(self,actors):
#        # Adds links to all actors in the specified dictionary, on the basis that all destinations now exist
#        for actor in actors.values():
#            for req in actor.requirements.values():
#                if hasattr(actor,'members') and len(req.components)>0:
#                    for host in actor.members.values(): self.__linkHostRequirement(host,req)
#                elif len(req.components)>0:
#                    self.__linkHostRequirement(actor,req)
#        
#    def __linkHostRequirement(self,host,requirement):
#        # Adds requirement/component/deployment linkage for a single host
#        for cmp_name in sorted(requirement.components.keys()):
#            if cmp_name in host.expected_deployments.keys():
#                # If this deployment is already linked to the host, just add the requirement
#                host.expected_deployments[cmp_name].addRequirement(requirement)
#            else:
#                # Must create a new deployment
#                depl = Deployment(host, self.components[cmp_name])
#                depl.addRequirement(requirement)
#   
#
#    def __buildComponentSet(self,x_components,x_languages,type_name):
#
#        # Create a dictionary of all components of the specified type, given the XML actors element
#        ret = {}
#        for x_cmp in x_components.findall(type_name):
#            ob = SiteObject(x_cmp)
#            ob.type = type_name
#
#            #If this is a CM location... with no filename use the component name, with no repo name use default        
#            if x_cmp.get('cm_location') is not None:
#                if x_cmp.get('cm_filename') is None:
#                    ob.cm_filename = ob.name
#                if x_cmp.get('cm_repository') is None:
#                    ob.cm_repository = self.default_cm_repository
#            #If this is a RepoApplication with no package, use the component name
#            if x_cmp.tag == "RepoApplication" and x_cmp.get('package') is None:
#                ob.package = ob.name
#            
#            #Initially just store the dependent names; objects will be linked during linkComponentSet
#            ob.dependencies = {}
#            for x_dep in x_cmp.findall('RequiredComponent'):
#                ob.dependencies[x_dep.get('name')] = None
#            #Any script language adds extra dependencies
#            if x_cmp.get('language') is not None:
#                for x_lng in x_languages.findall('Language'):
#                    if x_lng.get('name') == x_cmp.get('language'):
#                        for x_app in x_lng.findall('Application'):
#                            ob.dependencies[x_app.get('name')] = None
#                        break
#
#            # Build a dictionary of expected deployments, linking each to the actual hosts and ourselves
#            # If filename is not specified use that of the component
#            ob.deployments = {}
#            for x_depl in x_cmp.findall('Deployment'):
#                host_set = self.actors[x_depl.get('host_set')]
#                if hasattr(host_set,'members'):
#                    for host in host_set.members.values():
#                        depl = Deployment(host, ob)
#                        depl.setToXml(x_depl)
#                else:
#                    depl = Deployment(host_set, ob)
#                    depl.setToXml(x_depl)
#
#            ret[ob.name] = ob
#
#        return ret
#        
#
#    def __linkComponentSet(self,components):
#        # Adds links to all components in the specified dictionary, on the basis that all destinations now exist
#        for cmp in components.values():
#            for dep_name in sorted(cmp.dependencies.keys()):
#                cmp.dependencies[dep_name] = self.components[dep_name]
#        
#
#
#if __name__ == '__main__':
#    # Test Script
#    sd = SiteDescription("/home/jody/files/computing/requirements/SiteDescription.xml")
#
#    
#    
