#====================================================
# DateBatch
#====================================================
# $RCSfile$
# $Revision$
# Last revised by $Author$
# Last revised on $Date$
#====================================================
# DateBatcher class to call specified functions at
# date based intervals, equivalent to DateBatch.exe
#====================================================

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

    def __addLogEntry(self,summary,reason):
        """Add an line starting with summary to the log, if it was set"""
        if(self.log):
            log_file = open(self.log,"w+")
            line = summary + datetime.now().isoformat()
            if reason:
                line += " ("+reason+")"
            log_file.write(line+"\n")
            log_file.close()


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


    def runRequired(self):
        """Returns True if a run is required, or False if not"""
        self.validate()
        last_run = None

        if self.dirMode:
            # Find the latest dated subdirectory if we're in directory mode
            for string in os.listdir(self.dir):
                mo = re.search(r"(\d{4})-(\d{2})-(\d{2})",string)
                if mo is not None:
                    this_run = date(*[int(x) for x in mo.groups()])
                    if (last_run is None) or this_run>last_run:
                        last_run = this_run
        else:
            #TODO find last date from log file here
            pass

        # Return true if we've never been run or if the last run
        # was within the spacing interval
        today = date.today()
        return (last_run == None or (today-last_run).days >= self.spacing)


    def forceExecute(self):
        """Force the run to be performed even if not required"""
        self.validate()
        today = date.today()

        # If we are directory based and we've reached the
        # count limit, delete the oldest directory
        if self.dirMode:
            dated_dirs = []
            for string in os.listdir(self.dir):
                mo = re.search(r"(\d{4})-(\d{2})-(\d{2})",string)
                if mo is not None:
                    dated_dirs.append(date(*[int(x) for x in mo.groups()]))
            dated_dirs.sort().reverse()
            while dated_dirs.size() >= self.count:
                shutil.rmtree(dated_dirs.pop())

            # Create the directory if necessary
            if today.isoformat() not in dated_dirs:
                os.mkdir(self.dir + "/" + today.isoformat())

        # Run the command, trapping errors
        error = ""
        try:
            self.function
        except Exception as e:
            error = str(e)

        # Add a line to the log even if we fail
        if self.logFile:
            if error:
                __addLogEntry(_FAIL_TEXT,error)
            else:
                __addLogEntry(_GOOD_TEXT)

    def execute(self):
        """Perform the run, but only if required"""
        self.validate()


