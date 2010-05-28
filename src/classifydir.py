#========================================================
# ClassifyDir.py
#========================================================
# $HeadURL:                                             $
# Last $Author: jody $
# $Revision: 742 $
# $Date: 2009-12-28 02:23:37 -0600 (Mon, 28 Dec 2009) $
#========================================================
# Class to build a hierarchy of directories with 
# information about how they should be backed up, 
# as determined by .classify files
#========================================================


#Imports (all are used even if eclipse struggles)
import os       #@UnusedImport
import stat
import operator

__author__="Jody"


MAGIC_FILE=".classify"
T_T="TOTAL"

required_settings = {
    'volume':[
        ('small','HDD, CF, 4 copies per SD'),
        ('medium','HDD, CF, 2 copies per SD'),
        ('large','HDD, CF backup only'),
        ('huge','HDD backup only'),
        ('none','Not included in backup'),
    ],
    'protection':[
        ('secret','Always encrypted'),
        ('confidential','Encrypted on removable media'),
        ('restricted','Access control only'),
        ('none','No controls or encryptions'),
    ],
    'recurse':[
        ('true', 'Apply to child directories'),
        ('false','Do not apply to child directories'),
    ],
    'compress':[
        ('true', 'Data will compress successfully'),
        ('false','Data will not compress significantly'),
    ],
} 

optional_settings = ['name']


# Status = implicit,explicit,undefined

 
              
class ClassifiedDir(object):
    """A class to store and report the classification of a single
    directory, as declared by magic .classify files."""


    def classDirList(self,volume=None,protection=None):
        """Return a list of all child directory classifydir objects
        filtering to volume and/or protection where specified"""
        ret = []
        if self.status == 'explicit' and self.__matches(volume,protection):
            ret.append(self)
        for child in self.children:
            ret += child.classDirList(volume,protection)
        return ret

    
    def dirList(self,volume=None,protection=None):
        """Return a list of all child directory (volume,protection,compress,rel_path,name)
        tuples filtering to volume and/or protection where specified"""
        ret = []
        if self.__matches(volume,protection):
            ret.append([self.volume,self.protection,self.compress,self.rel_path,self.name])
        for child in self.children:
            ret += child.dirList(volume,protection)
        return ret

    def totalSize(self,volume=None,protection=None):
        """Return total size of directory and all children, filtering
        to volume and/or protection where specified"""
        if self.size == None:
            return None
        total = self.size if self.__matches(volume,protection) else 0
        for child in self.children:
            total += child.totalSize(volume,protection)
        return total

    def fileCount(self,volume=None,protection=None):
        """Return total number of files in directory and all children, 
        filtering to volume and/or protection where specified"""
        if self.file_count == None:
            return None
        total = self.file_count if self.__matches(volume,protection) else 0
        for child in self.children:
            total += child.fileCount(volume,protection)
        return total


    def dirCount(self,volume=None,protection=None):
        """Return total number of directories in directory and all  
        children, filtering to volume and/or protection where specified"""
        if self.file_count == None:
            return None
        total = 1 if self.__matches(volume,protection) else 0
        for child in self.children:
            total += child.dirCount(volume,protection)
        return total

    def preferredMechanism(self):
        """Return the preferred mechanism for backing up the directory
        according to the classification and compression: one of
        jxx or zip or copy"""
        if self.protection == 'secret' or self.protection == 'confidential':
            return 'jxx'
        elif self.compress or not self.recurse:
            return 'zip'
        else:
            return 'copy'

    def __matches(self,volume,protection):
        return (self.status != 'undefined' and 
            (volume==None or volume==self.volume) and 
            (protection==None or protection==self.protection))

    def printSummary(self):
        """Print a nested tree of all directories"""
        self.__printSummary(0)

    def __printSummary(self,depth):
        """Internal recursive function to print a nested tree of all directories"""
        if self.status == 'undefined':
            tag = '  -  '
        elif self.status == 'implicit':
            tag = '  >  '
        elif self.recurse:
            tag = "[{},{}]".format(self.volume[0].upper(),self.protection[0].upper())
        else:
            tag = "({},{})".format(self.volume[0].upper(),self.protection[0].upper())
        
        if self.base_name != self.name:
            qname = "{} <{}>".format(self.base_name,self.name)
        else:
            qname = self.base_name

        if self.size != None:
            line = "{}{}{}{: <7}{}{}".format("  "*depth,qname," "*(45-len(qname)-depth),
                                        self.__humanSize(self.totalSize())," "*(8-depth),tag)
        else:
            line = "{}{}{}{}".format("  "*depth,qname," "*(50-len(qname)-depth*2),tag)
        
        print(line)
        
        for child in self.children:
            child.__printSummary(depth+1)
        if not self.completed:
            print("{}<any extra directories not shown>".format("  "*(depth+1)))


    def printTable(self):
        """Function to print a grid of file/dir count by classification"""
        protections = [opt[0] for opt in required_settings['protection']] + [None]
        volumes = [opt[0] for opt in required_settings['volume']] + [None]
        
        #Calculate the contents of each cell first
        entries = [[('','','')]+[('',T_T,'') if v==None 
            else ('',v.capitalize(),'') for v in volumes]] 
        for p in protections:
            row_data = [('',T_T if p==None else p.capitalize(),'')]
            for v in volumes:
                files = self.fileCount(v,p)
                dirs = self.dirCount(v,p)
                size = self.totalSize(v,p)
                if files==None:
                    row_data.append(('',"N/A",''))
                elif files>0:
                    row_data.append((str(files),str(dirs),self.__humanSize(size)))
                else:
                    row_data.append(('','-',''))
            entries.append(row_data)
        
        #Summarize the widest thing in each column
        widths = []
        for c in range(len(entries[0])):
            widths.append(0)
            for r in range(len(entries)):
                widths[c] = max([widths[c]]+[len(s) for s in entries[r][c]])
            #widths.append(max([len(entries[r][c]) for r in range(len(entries))]))

        #Build standard strings for the header and divider
        hdr = ' ' + ' '*(widths[0]+2) + '+'
        div = '+' + '-'*(widths[0]+2) + '+'
        for w in widths[1:]:
            hdr += '-'*(w+2) + '+'
            div += '-'*(w+2) + '+'
            
                
        #Then do the work
        print(hdr)
        for r in range(len(entries)):
            lines = [' ' if r==0 else '|']*3
            for c in range(len(widths)):
                fmt = " {0: " + ('>' if c==0 else '^') + str(widths[c]) + "} |"
                for l in range(3):
                    lines[l] += fmt.format(entries[r][c][l])
            for line in lines:
                print(line)
            print(div)
        



    def __humanSize(self,bytes):
        """Return number of bytes rounded to a sensible scale"""
        """TODO: Put this in a standard library somewhere"""
        sz = bytes
        for ut in ['B','kB','MB','GB','TB']:
            if sz<10 and ut!='B ':
                return "{0:.1f} {1}".format(sz,ut)
            elif sz<1024:
                return "{0:.0f} {1}".format(sz,ut)
            sz /= 1024
        return "ERR"

            
    def __init__(self,base_path,get_all,rel_path='',parent=None):
        """Initialize all attributes"""
        self.base_name = os.path.basename(rel_path)
        self.name = self.base_name
        self.rel_path = rel_path
        self.full_path = os.path.join(base_path,rel_path)
        self.children = []

        magic = os.path.join(self.full_path,MAGIC_FILE)

        #Detect and read the magic file if appropriate
        if os.path.isfile(magic):
            if parent and parent.status != 'undefined' and parent.recurse:
                raise Exception("Classification file " + magic +
                                " inside recursively classified directory")
            self.status = 'explicit'
            self.__readFile()
        else:
            if not parent or parent.status == 'undefined':                
                self.status = 'undefined'
                self.volume = 'none'
                self.protection = 'none'
                self.compress = False
                self.recurse = False
            elif not parent.recurse:
                raise Exception("Directory " + self.full_path + " is inside "
                                "non-recursive classified directory " +
                                "but does not contain classification file")
            else:
                self.status = 'implicit'
                self.volume = parent.volume
                self.protection = parent.protection
                self.compress = parent.compress
                self.recurse = parent.recurse
                    
        #If we are recursive and haven't been asked to get everything 
        #this is now good enough
        self.completed = (get_all or self.status=='undefined' or not self.recurse)
        self.size = 0 if get_all else None
        self.file_count = 0 if get_all else None
        
        if not self.completed:
            return
            
        for entry in os.listdir(self.full_path):
            status = os.stat(os.path.join(self.full_path,entry))
            if stat.S_ISDIR(status.st_mode):
                child = ClassifiedDir(base_path,get_all,
                                      os.path.join(self.rel_path,entry),self)
                self.children.append(child)
            elif get_all:
                self.size += status.st_size
                self.file_count += 1
        self.children.sort(key=operator.attrgetter('full_path'))

    

    def __readFile(self):
        """Adds hash values describing the required_settings in magic file at path"""
    
        # First get another function to put each line into a hash
        magic = os.path.join(self.full_path,MAGIC_FILE)
        hsh = {}

        f = open(magic, 'r')
        try:
            for ln in f:
                self.__readLine(hsh,ln)    
        except Exception as e:
            raise Exception("Error parsing {}: {}".format(magic,str(e)))
        finally:
            f.close()
        
        #Check the hash contains everything we wanted
        for setting in required_settings.keys():
            if setting not in hsh.keys():
                raise Exception("{} not specified in {}".format(setting,magic))
            
        #Then use it to populate the object
        self.volume     = hsh['volume']
        self.protection = hsh['protection']
        self.recurse    = hsh['recurse']
        self.compress   = hsh['compress']
        if 'name' in hsh.keys():
            self.name   = hsh['name']
        else:
            self.name   = self.base_name


    def __readLine(self,hsh,line):
        """Adds a single hash value to hsh based on a single setting line"""

        pre_comment = line.split('#')[0].lower().strip()
        if len(pre_comment) == 0:
            return

        sections = pre_comment.split('=')
        if len(sections) != 2:
            raise Exception("Line '" + line + "' not understood")        
        (setting,value) = [x.strip() for x in sections]
        
        # Must not have been used before and must be in optional, or in
        # required and matching one of the enumerations
        if setting in hsh.keys():
            raise Exception("Duplicate setting for {}".format(setting))
        if setting in required_settings.keys():
            if value not in [set[0] for set in required_settings[setting]]:
                raise Exception("Invalid value '{}' for {}".format(value,setting))           
        elif not setting in optional_settings:
            raise Exception("Unknown setting '{}'".format(setting))            

        # Do the setting, converting boolean words to true boolean
        if value == 'true':
            hsh[setting] = True
        elif value == 'false':
            hsh[setting] = False
        else:
            hsh[setting]=value
