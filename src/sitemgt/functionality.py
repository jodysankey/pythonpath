#========================================================
# functionality.py
#========================================================
# $HeadURL:                                             $
# Last $Author: jody $
# $Revision: 742 $
# $Date: 2009-12-28 02:23:37 -0600 (Mon, 28 Dec 2009) $
#========================================================
# PublicPermissions: True
#========================================================
# Classes to represent the functionality of a site;  
# level level Capabilities, SystemRequirements, and 
# ActorRequirements
#========================================================


from .general import SiteObject, Health, CheckOutcome, OFF, UNKNOWN, GOOD, FAULT, DEGD, FAIL
from .paths import CHECKS_DIR

from datetime import datetime, timedelta
import os

#Library functions
def _readLastLineFromFile(filename):
    with open(filename, 'r') as fh:
        for line in fh: pass
        return line


class SystemRequirement(SiteObject):
    """A requirement to be met by the entire system"""

    _expand_dicts = [['actor_requirement_dict'],['actor_requirement_dict']]
    _expand_objects = [['capability']]
    _importance_dict = {'5':'Critical', '4':'High', '3':'Medium', '2':'Low', '1':'Minimal'}

    def __init__(self, x_element, capability):
        """Initialize the object"""
        
        # Set basic properties
        SiteObject.__init__(self,x_element,'systemrequirement')
        self.text = self.text.replace("%","The System")
        self.capability = capability
        self.name = self.uid
        self.importance_text = self._importance_dict[self.importance]

        # Build lists of all manual and automatic checks and determine the verification type
        self.automatic_checks = []
        self.manual_checks = []
        for x_ck in x_element.findall('AutomaticCheck'):
            self.automatic_checks.append(AutomaticCheck(x_ck, self))
        for x_ck in x_element.findall('ManualCheck'):
            self.automatic_checks.append(ManualCheck(x_ck, self))
        if len(self.automatic_checks) > 0:
            self.verification = "ByAutomaticTest"
        elif len(self.manual_checks) > 0:
            self.verification = "ByManualTest"
        elif x_element.find("VerificationByDesign") is not None:
            self.verification = "ByDesign"
        elif x_element.find("VerificationByInstallation") is not None:
            self.verification = "ByInstallation"
        else:
            self.verification = "ToBeDefined"

        # Create dictionary and list of requirement UIDs, to be replaced with the requirements at link time
        self.actor_requirement_dict = {}
        self.actor_requirement_list = []
        for x_ar in x_element.findall('Requirement'):
            self.actor_requirement_dict[x_ar.get('uid')] = None
            self.actor_requirement_list.append(x_ar.get('uid'))

    def _crossLink(self, siteDescription):
        """Initialize references to other objects within the site description"""
        for idx in range(len(self.actor_requirement_list)):
            ar = siteDescription.actor_requirement_dict[self.actor_requirement_list[idx]]
            self.actor_requirement_dict[ar.uid] = ar
            self.actor_requirement_list[idx] = ar
            ar.system_requirements[self.uid] = self

#        for ar_uid in sorted(self.actor_requirement_dict.keys()):
#            ar = siteDescription.actor_requirement_dict[ar_uid]
#            self.actor_requirement_dict[ar_uid] = ar
#            ar.system_requirements[self.uid] = self

    def hostSets(self):
        """Return an set of supporting hosts and host groups"""
        return set([ar.actor for ar in self.actor_requirement_dict.values() if ar.actor.isHostSet()])
            
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
        return set([ar.actor for ar in self.actor_requirement_dict.values() if not ar.actor.isHostSet()])

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

    def _setHealthAndStatus(self):
        """Determines health of the system requirement, based on health of its verification strategy, 
        check results, and the decomposition"""
        # Failure to fully decompose to a lower level means we are not healthy
        if self.decomposition == 'None':
            self._health = FAIL
            self._status = "No decomposition"
        elif self.verification == "ByDesign":
            self._health = GOOD
            self._status = "Functional"
        elif self.verification == "ByManualTest":
            self._health = OFF
            self._status = "Tested manually"
        elif self.verification == "ByManualTest":
            fail_count = len([x for x in self.automatic_checks if x.health() == FAIL])
            stale_count = len([x for x in self.automatic_checks if x.health() == DEGD])
            if fail_count > 0:
                self._health = FAIL
                self._status = "Tests failing"
            elif stale_count > 0:
                self._health = DEGD
                self._status = "Tests stale"
            else:
                self._health = GOOD
                self._status = "All tests pass"
        elif self.verification == "ToBeDefined":
                self._health = DEGD
                self._status = "Verification not determined"
        elif self.decomposition == 'Partial':
            self._health = DEGD
            self._status = "Partial requirement decomposition"
        elif self.decomposition == 'Blemished':
            self._health = FAULT
            self._status = "Blemished requirement decomposition"
        else:
            #TODO: work out how to set health based on software installation when that matters
            self._health = OFF
            self._status = "Reached default case"


class AutomaticCheck(SiteObject):
    """An automatic test to determine whether a system capability is being met"""
    # No children to expand
    def __init__(self, x_element, system_requirement):
        SiteObject.__init__(self,x_element,'automaticcheck')
        self.name = self.logfile
        self.system_requirement = system_requirement
        if not hasattr(self,"maxStalenessDays"):
            self.maxStalenessDays = 2
        self.recheckResult()

    def _qualifiedFileName(self):
        """Gets the log file name"""
        return os.path.join(CHECKS_DIR, self.logfile)

    def recheckResult(self):
        """Sets the last_result field based on the current check file."""
        # Clear previous outcome, assume failure until success is acheived
        self.last_result = None
        self.stale = True
        if not os.path.exists(self._qualifiedFileName()):
            self.result_error = "File not found"
        else:
            result_line = _readLastLineFromFile(self._qualifiedFileName())
            try:
                self.last_result = CheckOutcome.createFromFileString(result_line)
                self.stale = self.last_result.isStale(self.maxStalenessDays)
            except ValueError as ex:
                self.result_error = str(ex)

    def _setHealthAndStatus(self):
        """Determines health of the check based on the staleness and pass/fail.
        Assume the results have already been checked and do not recheck"""
        if self.stale:
            self._health = DEGD
            self._status = "Stale"
        elif self.last_result.success:
            self._health = GOOD
            self._status = "Passed"
        else:
            self._health = FAIL
            self._status = "Failed"



class ManualCheck(SiteObject):
    """An manual test to determine whether a system capability is being met"""
    # No children to expand
    def __init__(self, x_element, system_requirement):
        SiteObject.__init__(self,x_element,'manualcheck')
        self.system_requirement = system_requirement

    def _setHealthAndStatus(self):
        """Determines the [fixed] health of the check.""" 
        self._health = OFF
        self._status = "ManuallyAssured"


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
        self.primary_components = {}
        self.components = {}
        self.deployments = {}
        for x_cmp in x_element.findall('Component'):
            self.primary_components[x_cmp.get('name')] = None

    def _crossLink(self, siteDescription):
        """Initialize references to other objects within the site description"""
        for cmp_name in sorted(self.primary_components.keys()):
            cmp = siteDescription.components[cmp_name]
            self.primary_components[cmp_name] = cmp
    
    def htmlName(self):
        """Overridden to include a target within the actor page"""
        return self.actor.htmlName() + "#" + self.uid

    def _setHealthAndStatus(self):
        """Determines health of the actor requirement, based on health of its associated deployments"""
        if self._health is None:
            if not self.actor.isHostSet():
                # User based requirement_dict cannot be monitored
                self._health = OFF
                self._status = "UserBased"
            elif len(self.deployments)==0:
                # Requirements with no software cannot be monitored
                self._health = OFF
                self._status = "NoDeployments"
            else:
                self._health = Health.amortized([d.functionalHealth() for d in self.deployments.values()])
                self._status = "Deployments {}".format(self._health)


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
    
    _expand_dicts = [['responsibility_dict','requirement_dict']]
    #Translation table from system requirement importance and health to own health
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
        # Populate a list (for order) and dict (for lookup) of all child requirements    
        self.requirement_dict = {}
        self.requirement_list = []
        for x_sr in x_element.findall('SystemRequirement'):
            sr = SystemRequirement(x_sr, self)
            self.requirement_dict[sr.uid] = sr
            self.requirement_list.append(sr)
        # Populate a list and dict of all child responsibilities        
        self.responsibility_dict = {}
        self.responsibility_list = []
        for x_rsp in x_element.findall('UserResponsibility'):
            rsp = ActorResponsibility(x_rsp, self)
            self.responsibility_dict[rsp.user_set] = rsp
            self.responsibility_list.append(rsp)
        for x_rsp in x_element.findall('HostResponsibility'):
            rsp = ActorResponsibility(x_rsp, self)
            self.responsibility_dict[rsp.host_set] = rsp
            self.responsibility_list.append(rsp)
            
    def _crossLink(self, siteDescription):
        """Initialize references to other non capability objects"""
        for req in self.requirement_dict.values():
            req._crossLink(siteDescription)
        for resp in self.responsibility_dict.values():
            resp._crossLink(siteDescription)
            
    def _setHealthAndStatus(self):
        """Determines health of the system requirement, based on health of its actor requirement_dict"""
        self._health = Health.worst([self._translation[sr.importance][sr.health] for sr in self.requirement_list])
        self._status = self._health.name