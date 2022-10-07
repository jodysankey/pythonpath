#========================================================
# PublicPermissions: True
#========================================================

""" DateBatcher class to call specified functions at date based intervals,
equivalent to DateBatch.exe"""

import os
import re
import shutil
from datetime import date, datetime

_GOOD_TEXT = "RUN    "
_FORCE_TEXT = "FORCE  "
_FAIL_TEXT = "FAIL   "
_SKIP_TEXT = " -     "


class DateBatcher:
    """A class to perform the same function as the DateBatch executable.

    Initialize with either setUsingDir or setUsingLog before use
    or all other functions will fail."""

    def __init__(self, output_dir, spacing, count, dir_mode, function, log_path):
        """Initialize all attributes to the supplied inputs

        output_dir   -- Parent directory for dated subdirectories, or directory passed
                        directly to the function in log mode.
        spacing      -- Minimum number of days between runs.
        count        -- Number of runs to maintain in directory mode.
        function     -- Python function called with subdirectory to perform run.
        log_path     -- Optional log file to document run attempts."""
        self.output_dir = output_dir
        self.spacing = spacing
        self.count = count
        self.dir_mode = dir_mode
        self.function = function
        self.log_path = log_path

    @staticmethod
    def using_dir(output_dir, spacing, count, function, log_path=None):
        """Initialize class to create dated subdirectories within ouput_dir."""
        return DateBatcher(output_dir=output_dir,
                           spacing=spacing,
                           count=count,
                           dir_mode=True,
                           function=function,
                           log_path=log_path)

    @staticmethod
    def using_log(output_dir, spacing, function, log_path):
        """Initialize class to execute based on runs in a log."""
        return DateBatcher(output_dir=output_dir,
                           spacing=spacing,
                           count=1,
                           dir_mode=False,
                           function=function,
                           log_path=log_path)

    def validate(self):
        """Throw an exception if the instance variables are not valid"""
        if self.count < 1 or self.spacing < 1:
            raise AttributeError
        if not self.output_dir:
            raise AttributeError
        if not self.function or not hasattr(self.function, '__call__'):
            raise AttributeError


    def last_success(self):
        """Return the date of the last successful run, or None otherwise"""
        self.validate()
        last_date = None

        if self.dir_mode:
            dated_dirs = self.__dated_dirs()
            if len(dated_dirs) > 0:
                return dated_dirs[0]
        elif os.path.isfile(self.log_path):
            with open(self.log_path, "r") as log_file:
                for line in log_file:
                    if line.startswith((_GOOD_TEXT, _FORCE_TEXT)):
                        match = re.search(r"(\d{4})-(\d{2})-(\d{2})", line)
                        if match is not None:
                            last_date = date(*[int(x) for x in match.groups()])
        return last_date

    def run_required(self):
        """Return True if a run is required, or False if not"""
        self.validate()
        last_success = self.last_success()
        today = date.today()
        return last_success is None or (today - last_success).days >= self.spacing

    def remove_excess_directories(self):
        """Remove the oldest subdirectories while count is above the max"""
        if not self.dir_mode:
            raise ValueError
        dated_dirs = self.__dated_dirs()
        while len(dated_dirs) > self.count:
            shutil.rmtree(os.path.join(self.output_dir, dated_dirs.pop().isoformat()))

    def force_execute(self):
        """Force the run to be performed even if not required"""
        self.__execute(True)

    def execute(self):
        """Perform the run, but only if required"""
        self.__execute(False)

        if len(self.output_dir) < 1:
            raise AttributeError

    def __dated_dirs(self):
        """Returns an ordered list of all date subdirectories, latest first"""
        assert self.dir_mode

        dated_dirs = []
        for string in os.listdir(self.output_dir):
            match = re.search(r"(\d{4})-(\d{2})-(\d{2})", string)
            if match is not None:
                dated_dirs.append(date(*[int(x) for x in match.groups()]))
        dated_dirs.sort()
        dated_dirs.reverse()
        return dated_dirs


    def __add_log_entry(self, summary, reason=None):
        """Add an line starting with summary to the log, if it was set"""
        if self.log_path:
            with open(self.log_path, "a+") as log_file:
                line = summary + datetime.now().isoformat()
                if reason:
                    line += " ("+reason+")"
                log_file.write(line+"\n")


    def __execute(self, force):
        """Perform the mechanics of a run, if required or if told to force"""
        self.validate()
        if not force and not self.run_required():
            self.__add_log_entry(_SKIP_TEXT)
            return

        today = date.today()
        adding_dir = False
        target = self.output_dir

        if self.dir_mode:
            target += "/" + today.isoformat()
            dated_dirs = self.__dated_dirs()
            # Create today's directory if necessary
            if today not in dated_dirs:
                os.mkdir(target)
                adding_dir = True

            # Now if we've reached the count limit, delete the oldest directory
            self.remove_excess_directories()

        # Run the command, trapping errors and removing the directory if
        # we just created it but the function failed
        try:
            self.function(target)
        except Exception as ex:
            self.__add_log_entry(_FAIL_TEXT, str(ex))
            if adding_dir:
                shutil.rmtree(target)
        else:
            if force:
                self.__add_log_entry(_FORCE_TEXT)
            else:
                self.__add_log_entry(_GOOD_TEXT)
