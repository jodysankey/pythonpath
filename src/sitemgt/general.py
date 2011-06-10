#========================================================
# siteobject.py
#========================================================
# $HeadURL:                                             $
# Last $Author: jody $
# $Revision: 742 $
# $Date: 2009-12-28 02:23:37 -0600 (Mon, 28 Dec 2009) $
#========================================================
# Base class for all SiteDescription objects
# initialized from XML elements
#========================================================

#Imports

class Health(object):
    """A simple class to represent and compare high level health states"""
    def __init__(self,value,name):
        self.value = value
        self.name = name

    def __str__(self):
        return self.name
    
    def __lt__(self,other):
        return self.value < other.value
    def __le__(self,other):
        return self.value <= other.value
    def __ge__(self,other):
        return self.value >= other.value
    

    @staticmethod
    def worst(list):
        """Returns the worst health from the set. Unknown trumps good, fault and off"""
        top = max(list)
        if top < DEGD and UNKNOWN in list: return UNKNOWN
        return top 

    @staticmethod
    def amortized(list):
        """Returns an combined health from the set. Generally returns the worst, but Fail
        mixed with anything better leads to only a Degd. Unknown trumps Good, Fault and Off"""
        top = max(list)
        if top < DEGD and UNKNOWN in list: return UNKNOWN
        if top is FAIL and len([x for x in list if (x>=GOOD and x<=DEGD)])>0 : return DEGD
        return top 



UNKNOWN = Health(-2,"unknown")
OFF = Health(-1,"unmonitored")
GOOD = Health(0,"good")
FAULT = Health(1,"fault")
DEGD = Health(2,"degrade")
FAIL = Health(3,"fail")


class SiteObject(object):
    """A simple class derived from an XML element"""
    
    _expand_dicts = []
    _expand_objects = []
    
    def __init__(self, x_element, type_name):
        """Initialize all XML attributes as properties, and sets a type name"""
        self._health = None
        self.type = type_name
        for (a_name, a_value) in x_element.items():
            self.__dict__[a_name] = a_value

    def __str__(self):
        """Return a string representation"""
        return "\n".join(self._lines(0))

    def _lines(self,tier):
        """Return a string representation as a line set, expanding dictionaries below assuming tier"""
        # Build a first line of our name, type, and non-dictionary attributes
        attribs = ", ".join([x+':' + str(self.__dict__[x]) for x in self.__dict__.keys() 
                             if x!='name' and x!='type' and type(self.__dict__[x]) == type('')])
        lines = ["{}::{} {}{}{}".format(type(self).__name__, self.name, '{', attribs, '}')]

        #Expand out all list on the expectation they will contain simple strings
        for list_name in [x for x in self.__dict__.keys() if type(self.__dict__[x]) == type(list())]:
            lines.append(" {} := {}".format(list_name,str(self.__dict__[list_name])))

        #Expand out all contents of all siteobjects we are meant to at this tier
        if tier < len(self._expand_objects):
            for ob_name in self._expand_objects[tier]:
                if hasattr(self,ob_name):
                    lines.append(" {} link :=".format(ob_name))
                    lines.extend(["  " + ln for ln in self.__dict__[ob_name]._lines(tier+1)]) 

        #Expand out all contents of all dictionaries we are meant to at this tier
        if tier < len(self._expand_dicts):
            for dict_name in self._expand_dicts[tier]:
                if hasattr(self,dict_name) and len(self.__dict__[dict_name])>0:
                    lines.append(" {} {} :=".format(len(self.__dict__[dict_name]),dict_name))
                    for ob in self.__dict__[dict_name].values():
                        lines.extend(["  " + ln for ln in ob._lines(tier+1)]) 
        return lines

    
    def resetHealth(self):
        """Clears the health attribute"""
        self._health = None

    def health(self):
        """Unless overridden we can't know health"""
        if self._health is None:
            self._health = UNKNOWN
        return self._health

    
    def htmlName(self):
        """Return the file name to be used for an associated html"""
        return self.type.lower().replace(' ','_') + "_" + self.name.replace(' ','_') + ".html"

    def htmlClass(self):
        """Return a class attribute based on the current health"""
        return ' class="{}"'.format(self.health().name)

