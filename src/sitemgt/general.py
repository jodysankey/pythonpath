#========================================================
# siteobject.py
#========================================================
# PublicPermissions: True
#========================================================
# Base class for all SiteDescription objects
# initialized from XML elements
#========================================================

from datetime import datetime, timedelta

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
    def __gt__(self,other):
        return self.value > other.value
    def __ge__(self,other):
        return self.value >= other.value

    @staticmethod
    def worst(comparison_list):
        """Returns the worst health from the supplied list. Unknown trumps good, fault and off"""
        top = max(comparison_list)
        if top < DEGD and UNKNOWN in comparison_list: return UNKNOWN
        return top

    @staticmethod
    def amortized(comparison_list):
        """Returns an combined health from the supplied set. Generally returns the worst, but Fail
        mixed with anything better leads to only a Degd. Unknown trumps Good, Fault and Off"""
        top = max(comparison_list)
        if top < DEGD and UNKNOWN in comparison_list: return UNKNOWN
        if top is FAIL and len([x for x in comparison_list if (x>=GOOD and x<=DEGD)])>0 : return DEGD
        return top

UNKNOWN = Health(-2,"unknown")
OFF = Health(-1,"unmonitored")
GOOD = Health(0,"good")
FAULT = Health(1,"fault")
DEGD = Health(2,"degrade")
FAIL = Health(3,"fail")

HEALTH_CALC_MARKER = "health_status_calculation_in_progress"

class CheckOutcome(object):
    """A single outcome of an automatic check, capable of writing and reading from a results file.
       Each line of the results file is in the form:
            datetime, outcome, [value], [threshold], description
       where datetime is local time and standard format, outcome is 'pass' or 'fail', and (if present)
       value and threshold are numbers. For laziness of CSV parsing, the description string does not
       contain any commas"""
    def __init__(self, success, description, value=None, threshold=None, timestamp=None):
        self.timestamp = datetime.now() if timestamp is None else timestamp
        self.success = (success is True)
        self.value = value
        self.threshold = threshold
        self.description = description.replace(',','-') #Note we avoid commas for simpler parsing

    def valueOrString(self, s):
        return s if self.value is None else str(self.value)
    def thresholdOrString(self, s):
        return s if self.threshold is None else str(self.threshold)
    def outcome(self):
        return 'PASS' if self.success else 'FAIL'

    def isStale(self, maxAgeDays):
        """Return true if the timestamp is older than current time by at least the specified number of days"""
        limit_timestamp = datetime.now() - timedelta(days=maxAgeDays)
        return (self.timestamp < limit_timestamp)

    def fileString(self):
        """Returns the standard string encoding of this result"""
        return ", ".join([
            self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            self.outcome(),
            self.valueOrString(''),
            self.thresholdOrString(''),
            self.description])
    @staticmethod
    def headerString():
        """Returns a commented header line for the results file"""
        return "# Timestamp       Outcome Value Threshold ResultDescription"

    #Factory methods for simple creation of each outcome, and from file
    @staticmethod
    def createSuccess(description, value=None, threshold=None):
        return CheckOutcome(True, description, value, threshold)
    @staticmethod
    def createFailure(description, value=None, threshold=None):
        return CheckOutcome(False, description, value, threshold)

    @staticmethod
    def createFromFileString(fileString):
        """Create a new object from the output of fileString"""
        components = [x.strip() for x in fileString.split(',')]
        if len(components) != 5:
            raise Exception('Invalid number of CSV elements ({})'.format(fileString))
        elif (components[1].upper() != "PASS" and components[1].upper() != "FAIL"):
            raise Exception('Invalid outcome format ({})'.format(components[1]))
        else:
            try:
                timestamp = datetime.strptime(components[0], "%Y-%m-%d %H:%M:%S")
                return CheckOutcome(
                    components[1].upper() == 'PASS',
                    components[4],
                    None if components[2] == '' else float(components[2]),
                    None if components[3] == '' else float(components[3]),
                    timestamp)
            except ValueError:
                raise ValueError('Invalid number or date format ({})'.format(fileString))

def initializeObjectFromXmlElement(obj, x_element, remap_dict):
    """Sets fields on an object equal to attributes on an XML element. If the attribute exists
    in remap_dict mapped to None it will be omitted, if the attribute exists in remap_dict
    mapped to a different string it will be output with this name"""
    for (att_name, att_value) in x_element.items():
        if att_name in remap_dict.keys():
            if remap_dict[att_name] is None:
                pass # Don't include this attribute
            else:
                setattr(obj, remap_dict[att_name], att_value)
        else:
            setattr(obj, att_name, att_value)

def initializeXmlElementFromObject(x_element, obj, remap_dict):
    """Sets attributes on an XmlElement equal to simple fields on a python object. If the field
    exists in remap_dict mapped to None it will be omitted, if the field exists in remap_dict
    mapped to a different string it will be output with this name"""
    for att_name in [x for x in obj.__dict__.keys() if type(obj.__dict__[x]) == type('')]:
        att_value = obj.__dict__[att_name]
        if att_name in remap_dict.keys():
            if remap_dict[att_name] is None:
                pass # Don't include this attribute
            else:
                x_element.set(remap_dict[att_name], att_value)
        else:
            x_element.set(att_name, att_value)


class SiteObject(object):
    """An abstract base class for site entities created using a XML etree.ElementTree.Element"""

    _expand_dicts = []
    _expand_objects = []

    def __init__(self, x_element, type_name):
        """Initialize all XML attributes as properties, and sets a typename name"""
        self._health = None
        self._status = None
        self.type = type_name
        initializeObjectFromXmlElement(self, x_element, {'status':'_status', 'health':'_health'})

    def __str__(self):
        """Return a string representation"""
        return "\n".join(self._lines(0))

    def _lines(self, tier):
        """Return a string representation as list of line strings. All basic attributes are included,
        and child objects are expanded if included in the _expand_dicts and _expand_objects lists as
        a function of Tier. In general fewer children are included at higher tiers, and children are
        call with a higher tier to limit recursion depth"""
        # Build a first line of our name, type, and non-dictionary attributes
        attribs = ", ".join([x+':' + str(self.__dict__[x]) for x in self.__dict__.keys()
                             if x!='name' and x!='type' and type(self.__dict__[x]) == type('')])
        lines = ["{}::{} {}{}{}".format(type(self).__name__, self.name, '{', attribs, '}')]

        # Expand out all lists on the expectation they will contain simple strings
        for list_name in [x for x in self.__dict__.keys() if type(self.__dict__[x]) == type(list())]:
            lines.append(" {} := {}".format(list_name,str(self.__dict__[list_name])))

        # Expand out all contents of all siteobjects we are meant to at this tier
        if tier < len(self._expand_objects):
            for ob_name in self._expand_objects[tier]:
                if hasattr(self,ob_name):
                    lines.append(" {} link :=".format(ob_name))
                    lines.extend(["  " + ln for ln in self.__dict__[ob_name]._lines(tier+1)])

        # Expand out all contents of all dictionaries we are meant to at this tier
        if tier < len(self._expand_dicts):
            for dict_name in self._expand_dicts[tier]:
                if hasattr(self,dict_name) and len(self.__dict__[dict_name])>0:
                    lines.append(" {} {} :=".format(len(self.__dict__[dict_name]),dict_name))
                    for ob in self.__dict__[dict_name].values():
                        lines.extend(["  " + ln for ln in ob._lines(tier+1)])
        return lines


    def resetHealth(self):
        """Clears the health and status attributes to force recalculation"""
        self._health = None

    @property
    def health(self):
        """Return the current health as an enumeration, requesting calculation if unavailable"""
        if hasattr(self,HEALTH_CALC_MARKER):
            raise Exception("Circular dependency calculating health and status of " + self.name)
        if self._health is None:
            setattr(self,HEALTH_CALC_MARKER,True)
            self._setHealthAndStatus()
            delattr(self,HEALTH_CALC_MARKER)
        return self._health

    @property
    def status(self):
        """Return the current health as an enumeration, requesting calculation if unavailable"""
        if hasattr(self,HEALTH_CALC_MARKER):
            raise Exception("Circular dependency calculating health and status of " + self.name)
        if self._status is None:
            setattr(self,HEALTH_CALC_MARKER,True)
            self._setHealthAndStatus()
            delattr(self,HEALTH_CALC_MARKER)
        return self._status

    def htmlName(self):
        """Return the file name to be used for an associated html"""
        return self.type.lower().replace(' ','_') + "_" + self.name.replace(' ','_') + ".html"

    def htmlClass(self):
        """Return a CSS class attribute based on the current health"""
        return ' class="{}"'.format(self.health.name)
