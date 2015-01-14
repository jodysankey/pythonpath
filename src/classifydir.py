#========================================================
# ClassifyDir.py
#========================================================
# $HeadURL:                                             $
# Last $Author: jody $
# $Revision: 742 $
# $Date: 2009-12-28 02:23:37 -0600 (Mon, 28 Dec 2009) $
#========================================================
# PublicPermissions: True
#========================================================
# Class to build a hierarchy of directories with 
# information about how they should be backed up, 
# as determined by .classify files
#========================================================

import base64
import hashlib
import os
import stat

__author__ = "Jody"

MAGIC_FILE = ".classify"

REQUIRED_SETTINGS = {
    'volume':[
        ('small', 'HDD, CF, 4 copies per SD', '\033[38;5;38m'),
        ('medium', 'HDD, CF, 2 copies per SD', '\033[38;5;47m'),
        ('large', 'HDD, CF backup only', '\033[38;5;190m'),
        ('huge', 'HDD backup only', '\033[38;5;220m'),
        ('none', 'Not included in backup', '\033[38;5;247m'),
    ],
    'protection':[
        ('secret', 'Always encrypted', '\033[38;5;165m'),
        ('confidential', 'Encrypted on removable media', '\033[38;5;196m'),
        ('restricted', 'Access control only', '\033[38;5;208m'),
        ('none', 'No controls or encryptions', '\033[38;5;216m'),
    ],
    'recurse':[
        ('true', 'Apply to child directories'),
        ('false', 'Do not apply to child directories'),
    ],
    'compress':[
        ('true', 'Data will compress successfully'),
        ('false', 'Data will not compress significantly'),
    ],
} 
OPTIONAL_SETTINGS = ['name']

VOLUMES = [entry[0] for entry in REQUIRED_SETTINGS['volume'] if entry[0] != 'none']
PROTECTIONS = [entry[0] for entry in REQUIRED_SETTINGS['protection']]

VOLUME_COLORS = {entry[0]: entry[2] for entry in REQUIRED_SETTINGS['volume']}
PROTECTION_COLORS = {entry[0]: entry[2] for entry in REQUIRED_SETTINGS['protection']}

# Status = implicit,explicit,undefined
 
              
class ClassifiedDir(object):
    """A class to store and report the classification of a single
    directory, as declared by magic .classify files."""

    def __init__(self, base_path, fetch_info, max_recursion_depth=999, rel_path=None, parent=None):
        """initialize a new ClassifiedDir object"""
        if rel_path is None:
            self.full_path = os.path.abspath(base_path)
            base_path, self.rel_path = os.path.split(self.full_path)
            self.base_name = self.rel_path
        else:
            self.full_path = os.path.join(base_path, rel_path)
            self.rel_path = rel_path
            self.base_name = os.path.basename(rel_path)

        self.parent = parent
        self.depth = parent.depth + 1 if parent else 0
        self.recursion_depth = 0
        self.deepest_explicit = -1
        self.children = []
        self.size = 0 if fetch_info else None
        self.file_count = 0 if fetch_info else None
        
        # detect and read the magic file if appropriate
        config_file = os.path.join(self.full_path, MAGIC_FILE)
        if os.path.isfile(config_file):
            if parent and parent.__status != 'undefined' and parent.recurse:
                raise Exception("classification file " + config_file +
                                " inside recursively classified directory")
            self.__status = 'explicit'
            self.__readConfigurationFile(config_file)
            self.__propogateDeepestExplicit()
        else:
            self.name = self.base_name
            if not parent or parent.__status == 'undefined':                
                self.__status = 'undefined'
                self.volume = None
                self.protection = None
                self.compress = False
                self.recurse = False
            elif not parent.recurse:
                raise Exception("Directory " + self.full_path + " is inside "
                                "non-recursive classified directory " +
                                "but does not contain classification file")
            else:
                self.__status = 'implicit'
                self.volume = parent.volume
                self.protection = parent.protection
                self.compress = parent.compress
                self.recurse = parent.recurse
                if parent.recurse:
                    self.recursion_depth = parent.recursion_depth + 1
        if (not self.recurse) or fetch_info or self.recursion_depth < max_recursion_depth:
            self.__readContents(base_path, fetch_info, max_recursion_depth)

    def descendants(self):
        """generator function for all descendant or self classifydir objects."""
        # Stack is a list of remaining node lists for each level in a DFS 
        to_visit = [self]
        while to_visit:
            node = to_visit.pop(0)
            yield node
            to_visit[:0] = node.children

    def descendantRoots(self):
        """generator function for descendant or self classifydirs that are an archive root."""
        for decendent in self.descendants():
            if decendent.isArchiveRoot():
                yield decendent
    
    def descendantMembers(self):
        """generator function for descendant or self classifydirs inside the current archive. This
        method may only be called on an archive root."""
        if not self.isArchiveRoot():
            raise Exception(self.base_name + ' is not an archive root') 
        for descendant in self.descendants():
            if descendant.archiveRoot() is self:
                yield descendant
    
    def totalSize(self):
        """return total size of directory and all children"""
        if self.size == None:
            return None
        else:
            return sum((cd.size for cd in self.descendants()))

    def totalFileCount(self):
        """return total number of files in directory and all children"""
        if self.file_count is None:
            return None
        else:
            return sum((cd.file_count for cd in self.descendants()))

    def archiveRoot(self):
        """return the classified dir at the root of this archive, or none if not archived"""
        if self.__status == 'undefined' or self.volume == 'none':
            return None
        elif self.__status == 'implicit':
            return self.parent.archiveRoot()
        else:
            return self

    def isArchiveRoot(self):
        """return true iff this directory is the root of an archive"""
        return self.__status == 'explicit' and self.volume != 'none'
        
    def archiveSize(self):
        """return total size of files in an archive when called on the root"""
        return sum(cd.size for cd in self.descendantMembers())

    def archiveFileCount(self):
        """return total number of files in an archive when called on the root"""
        return sum(cd.file_count for cd in self.descendantMembers())

    def archiveLastChange(self):
        """return greatest file modification time in an archive when called on the root"""
        return max(cd.last_change for cd in self.descendantMembers())

    def archiveHash(self):
        """return a string hash of file state when called on the root"""
        hasher = hashlib.md5()
        for cd in self.descendantMembers():
            hasher.update(cd.content_hash)
        return base64.urlsafe_b64encode(hasher.digest()[:6]).decode('utf-8')

    def archiveFilenames(self):
        """generator for all filenames within an archive when called on the root"""
        for cd in self.descendantMembers():
            files = next(os.walk(cd.full_path, topdown=True, followlinks=False))[2]
            for entry in sorted(files):
                entry_path = os.path.join(cd.full_path, entry)
                status = os.lstat(entry_path)
                if stat.S_ISREG(status.st_mode):
                    yield entry_path

    def volumeColor(self):
        """Returns an Xterminal control string for a color reflecting required volume"""
        return VOLUME_COLORS[self.volume]

    def protectionColor(self):
        """Returns an Xterminal control string for a color reflecting required protection"""
        return PROTECTION_COLORS[self.protection]


    def __readContents(self, base_path, fetch_info, max_recursion_depth):
        """"Adds child objects and optionally sizes based on directories inside our own"""
        dirs, files = next(os.walk(self.full_path, topdown=True, followlinks=False))[1:]
        for entry in sorted(dirs):
            child_path = os.path.join(self.rel_path, entry) 
            child = ClassifiedDir(base_path, fetch_info, max_recursion_depth, child_path, self)
            self.children.append(child)
        if fetch_info:
            self.last_change = 0
            hasher = hashlib.md5()
            for entry in sorted(files):
                status = os.lstat(os.path.join(self.full_path, entry))
                if stat.S_ISREG(status.st_mode):
                    self.size += status.st_size
                    self.file_count += 1
                    if status.st_mtime > self.last_change:
                        self.last_change = status.st_mtime
                    hasher.update(entry.encode('utf-8'))
                    hasher.update(int(status.st_mtime).to_bytes(8, byteorder='little'))
                    hasher.update(int(status.st_size).to_bytes(8, byteorder='little'))
            self.content_hash = hasher.digest()


    def __readConfigurationFile(self, file_path):
        """Adds values read from the configuration file at file_path. Legal
        settings are defined by REQUIRED_SETTINGS and OPTIONAL_SETTINGS."""
        f = open(file_path, 'r')
        try:
            for (tag, value) in [_parseLine(l) for l in f if _parseLine(l)]:
                self.__validateSetting(tag, value)
                setattr(self, tag, _stringBool(value))
            for setting in REQUIRED_SETTINGS.keys():
                if not hasattr(self, setting):
                    raise Exception("{} not specified".format(setting))
            if not hasattr(self, 'name'):
                self.name = self.base_name
        except Exception as e:
            raise Exception("Error parsing {}: {}".format(file_path, str(e)))
        finally:
            f.close()

    def __propogateDeepestExplicit(self):
        """Propogates the current depth through all ancestors with a lower value."""
        node = self
        while node and node.deepest_explicit < self.depth:
            node.deepest_explicit = self.depth
            node = node.parent

    def __validateSetting(self, tag, value):
        """Ensures the specified tag value pair is legal. Throws an exception if not."""
        if tag in REQUIRED_SETTINGS.keys():
            if value not in [vd[0] for vd in REQUIRED_SETTINGS[tag]]:
                raise Exception("Invalid value '{}' for {}".format(value, tag))
        elif tag not in OPTIONAL_SETTINGS:
            raise Exception("Unknown setting '{}'".format(tag))            
        if hasattr(self, tag):
            raise Exception("Duplicate setting for {}".format(tag))



def _parseLine(line):
    """If line is in the form Tag=value[#Comment] returns a (tag, value)
    tuple, otherwise returns None"""
    non_comment = line.split('#')[0].strip()
    if len(non_comment) > 0:
        tag_value = [x.strip() for x in non_comment.split('=')]
        if len(tag_value) != 2:
            raise Exception("Line '" + line + "' not understood")
        return (tag_value[0], tag_value[1])
    else:
        return None
    
def _stringBool(value):
    """Returns a matching boolean if the input is true or false, else no change."""
    if value == 'true': return True
    if value == 'false': return False
    return value
