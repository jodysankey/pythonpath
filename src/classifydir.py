"""Class to build a hierarchy of directories with information about
how they should be backed up, as determined by .classify files."""

#========================================================
# PublicPermissions: True
#========================================================

import base64
import hashlib
import os
import stat

# Filename containing settings for how to classify the directory.
MAGIC_FILE = ".classify"

# The following defined the keys and values that are allowed in the magic file.
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

# Used by dependant modules.
VOLUMES = [entry[0] for entry in REQUIRED_SETTINGS['volume'] if entry[0] != 'none']
PROTECTIONS = [entry[0] for entry in REQUIRED_SETTINGS['protection']]

VOLUME_COLORS = {entry[0]: entry[2] for entry in REQUIRED_SETTINGS['volume']}
PROTECTION_COLORS = {entry[0]: entry[2] for entry in REQUIRED_SETTINGS['protection']}

# Status is set on each `ClassifiedDir` based on the directory's relationship to the magic file:
# * explicit = This directory contained its own magic file defining how it should be backed up.
# * undefined = This directory does not contained a magic file and no ancestors have recursively
#               included it.
# * implicit = This directory inherits the settings of a magic file in an ancestor.


class ClassifiedDir:
    """A class to store and report the classification of a single
    directory, as declared by magic .classify files."""

    def __init__(self, base_path, fetch_info, max_recursion_depth=999, rel_path=None, parent=None):
        if rel_path is None:
            self.full_path = os.path.abspath(base_path)
            base_path, self.rel_path = os.path.split(self.full_path)
            self.base_name = self.rel_path
        else:
            self.full_path = os.path.join(base_path, rel_path)
            self.rel_path = rel_path
            self.base_name = os.path.basename(rel_path)

        self.parent = parent
        # The number of path segments from the highest level ancestor to this directory.
        self.depth = (parent.depth + 1) if parent else 0
        # The number of path segments from the nearest ancestor with a magic classification file
        # to this directory.
        self.recursion_depth = 0
        # The greatest number of path segments between this directory and a descendent with its
        # own magic classification file.
        self.deepest_explicit = -1
        # ClassifiedDir objects for each subdirectory.
        self.children = []
        # Total size of the files in the directory (not counting subdirs), in bytes.
        self.size = 0 if fetch_info else None
        # Number of files in the directory (not counting subdirs).
        self.file_count = 0 if fetch_info else None
        # Most recent modtime of any file in the directory (not including subdirs).
        self.last_change = 0 if fetch_info else None
        # Hash over the filenames, mtimes, and sizes of files in the directory
        # (not including subdirs).
        self.content_hash = b'' if fetch_info else None

        # Detect and read the magic file if appropriate
        config_file = os.path.join(self.full_path, MAGIC_FILE)
        if os.path.isfile(config_file):
            self.status = 'explicit'
            self._read_configuration_file(config_file)
            self._propogate_deepest_explicit()
        else:
            self.name = self.base_name
            if not parent or parent.status == 'undefined':
                self.status = 'undefined'
                self.volume = None
                self.protection = None
                self.compress = False
                self.recurse = False
            elif not parent.recurse:
                raise Exception("Directory " + self.full_path + " is inside "
                                "non-recursive classified directory " +
                                "but does not contain classification file")
            else:
                self.status = 'implicit'
                self.recurse = True
                self.recursion_depth = parent.recursion_depth + 1
                self.volume = parent.volume
                self.protection = parent.protection
                self.compress = parent.compress
        if (not self.recurse) or fetch_info or self.recursion_depth < max_recursion_depth:
            self._read_contents(base_path, fetch_info, max_recursion_depth)

    def descendants(self):
        """Generator function for all descendant or self classifydir objects."""
        # Stack is a list of remaining node lists for each level in a DFS
        to_visit = [self]
        while to_visit:
            node = to_visit.pop(0)
            yield node
            to_visit[:0] = node.children

    def descendant_roots(self):
        """Generator function for descendant or self classifydirs that are an archive root."""
        for decendent in self.descendants():
            if decendent.is_archive_root():
                yield decendent

    def descendant_attenuations(self):
        """Generator function for descendant or self classifydirs that stop recursive archiving."""
        for decendent in self.descendants():
            if decendent.is_attenuation():
                yield decendent

    def descendant_members(self):
        """Generator function for descendant or self classifydirs inside the current archive. This
        method may only be called on an archive root."""
        if not self.is_archive_root():
            raise Exception(self.base_name + ' is not an archive root')
        for descendant in self.descendants():
            if descendant.archive_root() is self:
                yield descendant

    def total_size(self):
        """Return total size of directory and all children."""
        return None if self.size is None else sum((cd.size for cd in self.descendants()))

    def total_file_count(self):
        """Return total number of files in the directory and all children."""
        return (None if self.file_count is None
                else sum((cd.file_count for cd in self.descendants())))

    def archive_root(self):
        """Return the classified dir at the root of this archive, or None if not archived."""
        if self.status == 'undefined' or self.volume == 'none':
            return None
        if self.status == 'implicit':
            return self.parent.archive_root()
        return self

    def is_archive_root(self):
        """Return true iff this directory is the root of an archive."""
        return self.status == 'explicit' and self.volume != 'none'

    def is_attenuation(self):
        """Return true iff this directory is the root of an archive."""
        return self.status == 'explicit' and self.volume == 'none'

    def archive_size(self):
        """Return total size of files in an archive when called on the root."""
        return (None if self.size is None else
                sum(cd.size for cd in self.descendant_members()))

    def archive_file_count(self):
        """Return total number of files in an archive when called on the root."""
        return (None if self.file_count is None else
                sum(cd.file_count for cd in self.descendant_members()))

    def archive_last_change(self):
        """Return greatest file modification time in an archive when called on the root."""
        return (None if self.last_change is None else
                max(cd.last_change for cd in self.descendant_members()))

    def archive_hash(self):
        """Return a string hash of file state when called on the root."""
        if self.content_hash is None:
            return None
        hasher = hashlib.md5()
        for desc in self.descendant_members():
            hasher.update(desc.content_hash)
        return base64.urlsafe_b64encode(hasher.digest()[:6]).decode('utf-8')

    def archive_filenames(self):
        """Generator for all filenames within an archive when called on the root."""
        for desc in self.descendant_members():
            #files = next(os.walk(desc.full_path, topdown=True, followlinks=False))[2]
            for entry in sorted(os.listdir(desc.full_path)):
                entry_path = os.path.join(desc.full_path, entry)
                status = os.lstat(entry_path)
                if stat.S_ISREG(status.st_mode):
                    yield entry_path

    def volume_color(self):
        """Returns an Xterminal control string for a color reflecting required volume."""
        return VOLUME_COLORS[self.volume]

    def protection_color(self):
        """Returns an Xterminal control string for a color reflecting required protection."""
        return PROTECTION_COLORS[self.protection]

    def _read_contents(self, base_path, fetch_info, max_recursion_depth):
        """"Adds child objects and optionally sizes based on directories inside our own."""
        try:
            dirs, files = next(os.walk(self.full_path, topdown=True, followlinks=False))[1:]
        except StopIteration:
            return
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

    def _read_configuration_file(self, file_path):
        """Adds values read from the configuration file at file_path. Legal
        settings are defined by REQUIRED_SETTINGS and OPTIONAL_SETTINGS."""
        f = open(file_path, 'r')
        try:
            for (tag, value) in [_parse_line(l) for l in f if _parse_line(l)]:
                self._validate_setting(tag, value)
                setattr(self, tag, _string_bool(value))
            for setting in REQUIRED_SETTINGS:
                if not hasattr(self, setting):
                    raise Exception("{} not specified".format(setting))
            if not hasattr(self, 'name'):
                self.name = self.base_name
        except Exception as ex:
            raise Exception("Error parsing {}: {}".format(file_path, str(ex)))
        finally:
            f.close()

    def _propogate_deepest_explicit(self):
        """Propogates the current depth through all ancestors with a lower value."""
        node = self
        while node and node.deepest_explicit < self.depth:
            node.deepest_explicit = self.depth
            node = node.parent

    def _validate_setting(self, tag, value):
        """Ensures the specified tag value pair is legal. Throws an exception if not."""
        if tag in REQUIRED_SETTINGS.keys():
            if value not in [vd[0] for vd in REQUIRED_SETTINGS[tag]]:
                raise Exception("Invalid value '{}' for {}".format(value, tag))
        elif tag not in OPTIONAL_SETTINGS:
            raise Exception("Unknown setting '{}'".format(tag))
        if hasattr(self, tag):
            raise Exception("Duplicate setting for {}".format(tag))



def _parse_line(line):
    """If line is in the form Tag=value[#Comment] returns a (tag, value)
    tuple, otherwise returns None."""
    non_comment = line.split('#')[0].strip()
    if len(non_comment) > 0:
        tag_value = [x.strip() for x in non_comment.split('=')]
        if len(tag_value) != 2:
            raise Exception("Line '" + line + "' not understood")
        return (tag_value[0], tag_value[1])
    return None


def _string_bool(value):
    """Returns the equivalent boolean if the input string is 'true' or 'false', else no change."""
    if value == 'true': return True
    if value == 'false': return False
    return value
