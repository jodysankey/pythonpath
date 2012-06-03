#========================================================
# DateBatch.py
#========================================================
# $HeadURL:                                             $
# Last $Author$
# $Revision$
# $Date$
#========================================================
# PublicPermissions: True
#========================================================
# DateBatcher class to call specified functions at date
# based intervals, equivalent to DateBatch.exe
#========================================================

#Imports
import os
import re
import shutil
from datetime import date, datetime

__author__="Jody"
__date__ ="$13/09/2009 7:27:58 PM$"

_GOOD_TEXT  = "RUN    "
_FORCE_TEXT = "FORCE  "
_FAIL_TEXT  = "FAIL   "
_SKIP_TEXT  = " -     "



class DateBatcher(object):
    """A class to perform the same function as the DateBatch executable.

    Initialize with either setUsingDir or setUsingLog before use
    or all other functions will fail."""

    def __init__(self):
        """Initialize all attributes to a standard default"""
        self.spacing = 0
        self.count = 0
        self.log = ""
        self.dir = ""
        self.dirMode = True
        self.function = None


    
    def setUsingDir(self,dir,spacing,count,function,log=""):
        """Initialize class to create dated subdirectories within dir.

        Dir      -- Parent directory for dated subdirectories
        Spacing  -- Minimum number of days between runs
        Count    -- Number of runs to maintain
        Function -- Python function called with subdirectory to perform run
        Log      -- Optional log file to document run attempts
        """
        self.spacing = spacing
        self.count = count
        self.dir = dir
        self.log = log
        self.function = function
        self.dirMode = True

    def setUsingLog(self,dir,spacing,function,log):
        """Initialize class to execute based on runs in a log.

        Dir      -- Directory passed to function
        Spacing  -- Minimum number of days between runs
        Function -- Python function called with directory to perform run
        Log      -- Log file used to track when runs are performed
        """
        self.spacing = spacing
        self.count = 1
        self.dir = dir
        self.log = log
        self.function = function
        self.dirMode = False


    def validate(self):
        """Throw an exception if the instance variables are not valid"""
        if self.count<1 or self.spacing<1: 
            raise AttributeError
        if len(self.dir)<1: 
            raise AttributeError
        if not self.function or not hasattr(self.function,'__call__'):
            raise AttributeError


    def lastSuccess(self):
        """Return the date of the last successful run, or None otherwise"""
        self.validate()
        last_date = None

        if self.dirMode:
            dated_dirs = self.__datedDirs()
            if len(dated_dirs)>0:
                return dated_dirs[0]
        elif os.path.isfile(self.log):
            for line in open(self.log,"r"):
                if(line.startswith((_GOOD_TEXT,_FORCE_TEXT))):
                    mo = re.search(r"(\d{4})-(\d{2})-(\d{2})",line)
                    if mo is not None:
                        last_date = date(*[int(x) for x in mo.groups()])
        
        return last_date


    def runRequired(self):
        """Return True if a run is required, or False if not"""
        self.validate()
        last_success = self.lastSuccess()
        today = date.today()
        return (last_success == None or (today-last_success).days >= self.spacing)


    def removeExcessDirectories(self):
        """Remove the oldest subdirectories while count is above the max"""
        if not self.dirMode: raise ValueError
        dated_dirs = self.__datedDirs()
        while len(dated_dirs) > self.count:
            shutil.rmtree(self.dir + "/" + dated_dirs.pop().isoformat())


    def forceExecute(self):
        """Force the run to be performed even if not required"""
        self.__execute(True)


    def execute(self):
        """Perform the run, but only if required"""
        self.__execute(False)

        if len(self.dir)<1: 
            raise AttributeError

            


    def __datedDirs(self):
        """Returns an ordered list of all date subdirectories, latest first"""
        assert self.dirMode
        
        dated_dirs = []
        for string in os.listdir(self.dir):
                mo = re.search(r"(\d{4})-(\d{2})-(\d{2})",string)
                if mo is not None:
                    dated_dirs.append(date(*[int(x) for x in mo.groups()]))
        dated_dirs.sort()
        dated_dirs.reverse()
        return dated_dirs


    def __addLogEntry(self,summary,reason=None):
        """Add an line starting with summary to the log, if it was set"""
        if(self.log):
            log_file = open(self.log,"a+")
            line = summary + datetime.now().isoformat()
            if reason:
                line += " ("+reason+")"
            log_file.write(line+"\n")
            log_file.close()


    def __execute(self, force):
        """Perform the mechanics or a run, if required or if told to force"""
        self.validate()
        if not force and not self.runRequired():
            self.__addLogEntry(_SKIP_TEXT)
            return
        
        today = date.today()
        adding_dir = False
        target = self.dir

        if self.dirMode:

            target += "/" + today.isoformat()
            dated_dirs = self.__datedDirs()
            # Create today's directory if necessary
            if today not in dated_dirs:
                os.mkdir(target)
                adding_dir = True
                
            # Now if we've reached the count limit, delete the oldest directory
            self.removeExcessDirectories()

        # Run the command, trapping errors and removing the directory if
        # we just created it but the function failed
        try:
            self.function(target)
        except Exception as e:
            self.__addLogEntry(_FAIL_TEXT,str(e))
            if adding_dir:
                shutil.rmtree(target)
        else:
            if force:   self.__addLogEntry(_FORCE_TEXT)
            else:       self.__addLogEntry(_GOOD_TEXT)
