#========================================================
# statusreport.py
#========================================================
# PublicPermissions: True
#========================================================
# Defines an expandable and XML portable report of the
# status for a host
#========================================================

import os
import socket
import subprocess
import re
from datetime import datetime
from xml.etree.ElementTree import ElementTree, Element, parse

import time_error
from sitemgt.general import initializeObjectFromXmlElement, initializeXmlElementFromObject

_ELEMENT_NAME = "Report"
_ROOT_NAME = "StatusReports"


def getHostName():
    return socket.gethostname().lower()

def getCurrentTime():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def getIpV4Address():
    # In the normal case we only expect one non-loopback address, but generate a
    # semicolon separated list for completeness
    addresses = []
    lines = subprocess.check_output(['ip','-o','-4','addr']).decode("utf-8").split("\n")
    for line in lines:
        mo = re.search(r"inet (\d+\.\d+\.\d+\.\d+/\d+)", line)
        # Strip local host for clarity
        if mo != None and mo.group(1) != '127.0.0.1/8':
            addresses.append(mo.group(1))
    return ";".join(addresses)

def getIpV6AddressCount():
    # Only trying to prove there are no v6 addresses, and I'm not completely sure what
    # one would look like if it existed anyway, so just get a count instead of the addresses
    lines = subprocess.check_output(['ip','-o','-6','addr']).decode("utf-8").split("\n")
    return len(lines)

def getKernelVersion():
    uname = subprocess.check_output(['uname','-a']).decode("utf-8")
    return uname.split(" ")[2]

def getTimeError():
    diff = time_error.getTimesAndDifference()['difference']
    return ("ERR" if diff is None else "{:+d}".format(diff))

def formatTimeError(value):
    try:                return "{:+d} seconds".format(int(value))
    except ValueError:  return value

def getFirstPrinterName():
    return getSecondWordOfFirstLine(['lpstat', '-p'], 'printer')

def getSecondWordOfFirstLine(command, sentinal_word):
    try:
        lines = subprocess.check_output(command).decode("utf-8").split("\n")
    except Exception:
        return 'ERR'
    if len(lines) > 0:
        words = lines[0].split()
        if len(words) > 2 and words[0] == sentinal_word:
            return words[1].strip("'`")
    return 'ERR'



# Define an ordered list of the fields we will define, including pointers to the
# functions used to calculate and optionally format them

_STANDARD_FIELDS = [
    {'name':'host', 'header':None, 'formatFn':None, 'calcFn':getHostName},
    {'name':'timestamp', 'header':'Date', 'formatFn':None, 'calcFn':getCurrentTime},
    {'name':'ip_v4', 'header':'IP Address', 'formatFn':None, 'calcFn':getIpV4Address},
    {'name':'ip_v6_count', 'header':None, 'formatFn':None, 'calcFn':getIpV6AddressCount},
    {'name':'kernel', 'header':'Kernel ', 'formatFn':None, 'calcFn':getKernelVersion},
    {'name':'time_error', 'header':'Time Error', 'formatFn':formatTimeError, 'calcFn':getTimeError},
    {'name':'printer_name', 'header':'Printer', 'formatFn':None, 'calcFn':getFirstPrinterName},
                   ]

_PREFIX_FIELDS = [
    {'prefix':'disk_', 'headerFn':None, 'formatFn':None, 'calcFn':getHostName},
    ]

_EXCLUDED_ATTRIBUTES = ['att_map']
_EXCLUSION_DICT = dict(zip(_EXCLUDED_ATTRIBUTES, [None]*len(_EXCLUDED_ATTRIBUTES)))

class HostStatusReport(object):
    """A single report of high level status for a host"""

    @staticmethod
    def createFromXmlElement(x_element):
        """Return a new status report object based on the supplied XML element"""
        report = HostStatusReport()
        initializeObjectFromXmlElement(report, x_element, {})
        report._buildAttrToPrefixMap()
        return report

    @staticmethod
    def createListFromXmlFile(filename, max_quantity):
        """Return a list of the first max_quantity reports found in the specified xml file"""
        reports = []
        root = parse(filename).getroot()
        for el in root.findall(_ELEMENT_NAME):
            reports.append(HostStatusReport.createFromXmlElement(el))
            if len(reports) >= max_quantity: break
        return reports

    @staticmethod
    def createFirstFromXmlFile(filename):
        """Return the first status report found in the specified xmlFile"""
        return HostStatusReport.createListFromXmlFile(filename, 1)[0]

    @staticmethod
    def createFromCurrentHostState():
        """Return a new status report object based on the supplied XML element"""
        report = HostStatusReport()
        for fld in _STANDARD_FIELDS:
            setattr(report, fld['name'], fld['calcFn']())
        report._buildAttrToPrefixMap()
        return report

    def _buildAttrToPrefixMap(self):
        """Create a map indexed by attribute name to the Field information about that attribute"""
        self.att_map = dict()
        # Adding all the standard fields which exist is easy
        for f in _STANDARD_FIELDS:
            if hasattr(self,f['name']):
                self.att_map[f['name']] = f
        # All remaining attributes should match exactly one of the prefix fields
        for a in [a for a in self.__dict__ if (a not in self.att_map and a not in _EXCLUDED_ATTRIBUTES)]:
            matching_pf = [pf for pf in _PREFIX_FIELDS if a.startswith(pf['prefix'])]
            if len(matching_pf) == 0:
                print("Discarding unknown attribute " + a)
            elif len(matching_pf) > 1:
                raise Exception("Found {} matching prefixes for attribute {}".format(len(matching_pf), a))
            else:
                self.att_map[a] = matching_pf[0]

    def writeToXmlElement(self):
        """Return a new xml element based on the current report state"""
        el = Element(_ELEMENT_NAME)
        initializeXmlElementFromObject(el, self, _EXCLUSION_DICT)
        return el

    def insertIntoXmlFile(self, filename):
        """Add the current object as the first report in the specified file, creating if necessary"""
        if not os.path.exists(filename):
            root = Element(_ROOT_NAME)
            tree = ElementTree(root)
        else:
            tree = parse(filename)
            root = tree.getroot()
        root.insert(0, self.writeToXmlElement())
        tree.write(filename, "UTF-8")

    def getAttributesAndHeaders(self):
        """Return an ordered list of (attribute_name,attribute_header) tuples for all attributes
        interesting enough to have a header"""
        ret = [(f['name'], f['header']) for f in _STANDARD_FIELDS if f['header']]
        #TODO: Go through all prefix fields looking for attributes which match, then using a fn to format the attribute name
        return ret

    def getFormattedAttribute(self, attribute_name):
        if attribute_name in self.att_map:
            fld = self.att_map[attribute_name]
            if fld['formatFn']:
                return fld['formatFn'](getattr(self,attribute_name))
            else:
                return str(getattr(self,attribute_name))
        else:
            return ""

    def __str__(self):
        return "\n".join(["{} := {}".format(x, getattr(self,x)) for x in self.__dict__.keys()])
