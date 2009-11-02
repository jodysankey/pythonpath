#====================================================
# BackupFunctions
#====================================================
# $RCSfile$
# $Revision$
# Last revised by $Author$
# Last revised on $Date$
#====================================================
# Functions  :  reportError
#               updateArchive
#====================================================
# Module containing various functions to assist with
# backup process
#====================================================


# Imports
import subprocess as sp         # Call ing
import shutil as su             # File operations
#import sys                     # Exit
import os                       # Shell
from datetime import datetime	# Current date and time



def reportError(subject, content):
    """Sends a failure email with the specified subject and turns the
    screen red. If "content" is a file, the email body is the contents
    of that file, otherwise the email body is the content string itself"""
    #Were we given a filename?
    try:
        os.stat(subject)
    except WindowsError:
        #No
        command = 'BLAT - -to jody@jsankey.com -subject "{}" -body "{}"'.format(subject, content)
    else:
        #Yes
        command = 'BLAT "{}" -to jody@jsankey.com -subject "{}"'.format(content, subject)
    #Call blat and color the screen
    sp.call(command, shell=True)
    os.system('COLOR 47')


def updateArchive(archive_name, source_dir, key,
    archive_dir = "\\\\NAS\\Jody\\NewArchives\\",
    log_dir     = "\\\\NAS\\Jody\\NewArchives\\"):
    """Handles updating a JCrypt archive from the specified directory,
    reporting any failures, maintaining a running log in the specified
    location, and a .err file in the log location which is empty if
    no errors ocurred. The JXX file is actually built in the user's
    temp directory for speed"""

    # First work out filenames
    working_dir = os.getenv("TEMP")+"\\"
    working_log  = working_dir + "jxx_build.log"
    working_jxx  = working_dir + archive_name + ".jxx"
    final_jxx    = archive_dir + archive_name + ".jxx"
    log_file     = log_dir + archive_name + ".log"
    err_file     = log_dir + archive_name + ".err"

    # Run JCrypt
    command = 'JCRYPT /MIRROR /E:S /KEY "{}" /ARCHIVE "{}" {} | TEE "{}"'.\
            format(key, working_jxx, source_dir, working_log)
    print("Running JCrypt to update {} ...".format(working_jxx))
    ret = sp.call(command,shell=True)

    # Report any failures and set an error file in the log directory
    if ret>0:
            reportError("FAILURE UPDATING "+archive_name+".jxx",working_log)
            su.copy(working_log,err_file)
    else:
            # If we succeed just truncate the last log to 0
            f = open(err_file,'w')
            f.close()

    #Get the times for both the updated archive and the master copy
    try:
            old_time = os.stat(final_jxx).st_mtime
    except WindowsError:
            old_time = 0
    new_time = os.stat(working_jxx).st_mtime
    file_updated = (new_time > old_time-60)

    # Copy the working archive, if it actually updated, and append to the log
    if file_updated:
            print("Copying updated {} ...".format(working_jxx))
            su.copy2(working_jxx,final_jxx)

    # Append results or a "NOP" to the log
    with open(log_file,'a') as lf:
        sep = "============================================\n"
        now = datetime.now()
        lf.write(sep)

        if file_updated or (ret>0):
            lf.write("{} (Return Code {})\n".format(now.ctime(),ret))
            lf.write("Old: {}\nNew: {}\n".format(old_time,new_time))
            lf.write(sep)
            with open(working_log,'r') as wf:
                for line in wf.readlines():
                    if len(line)>1: lf.write(line)
        else:
            lf.write("{} (No changes detected)\n".format(now.ctime()))
