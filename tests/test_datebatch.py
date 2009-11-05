from datetime import date, datetime, timedelta
import datebatch
import os
import shutil
import unittest


#test_path = os.getenv("TMP") + "/DateBatchTest" # TMP set to some hideous directory
test_path = r"C:\Temp\DateBatchTest"
test_file = "test.txt"
test_log = test_path + "/test.log"


def testFunction(dir):
    """Function suitable for datebatch use. Adds a date line to test_file"""
    file = open(dir + "/" + test_file,"a+")
    file.write("Ran test function " + datetime.now().isoformat() + "\n")
    file.close()

def exceptionFunction(dir):
    """Function suitable for datebatch use. Throws an exception"""
    raise AttributeError


class DateBatchTestCase(unittest.TestCase):

    def setUp(self):
        #Make sure we remove any existing test dir first, then create a new one
        try:
            os.stat(test_path)
        except WindowsError:
            pass
        else:
            shutil.rmtree(test_path)
        os.mkdir(test_path)
        
    def testInitializationRequirement(self):
        db = datebatch.DateBatcher()
        self.assertRaises(AttributeError,db.runRequired)
        self.assertRaises(AttributeError,db.forceExecute)
        self.assertRaises(AttributeError,db.execute)

    def testFunctionException(self):
        db = datebatch.DateBatcher()
        db.setUsingDir(test_path, 1, 1, exceptionFunction)
        db.execute()
        self.failUnless(db.runRequired(),"Did not require rerun following failure")


    def testDirBasedWithoutLog(self):
        #Init object
        db = datebatch.DateBatcher()
        today = date.today()
        db.setUsingDir(test_path, 3, 2, testFunction)

        #Test run required returns appropriate values
        req = db.runRequired()
        self.failUnless(req,"Did not require run on empty directory")
        os.mkdir(test_path + "/" + (today-timedelta(3)).isoformat())
        req = db.runRequired()
        self.failUnless(req,"Did not require run on out of date directory")
        db.setUsingDir(test_path, 4, 2, testFunction)
        req = db.runRequired()
        self.failIf(req,"Required run on in-date directory")

        #Test with log continues to test more complex conditions


    def testDirBasedWithLog(self):
        #Init object
        db = datebatch.DateBatcher()
        today = date.today()
        db.setUsingDir(test_path, 3, 2, testFunction, test_log)

        #Test run required returns appropriate values
        req = db.runRequired()
        self.failUnless(req,"Did not require run on empty directory")
        os.mkdir(test_path + "/" + (today-timedelta(3)).isoformat())
        req = db.runRequired()
        self.failUnless(req,"Did not require run on out of date directory")
        db.setUsingDir(test_path, 4, 2, testFunction, test_log)
        req = db.runRequired()
        self.failIf(req,"Required run on in-date directory")

        #Test run is executed when, and only when, it is required
        test_full_file = test_path+"/"+today.isoformat()+"/"+test_file
        db.setUsingDir(test_path, 3, 2, testFunction, test_log)
        db.execute()
        self.failUnless(os.path.exists(test_full_file),
            "Command did not execute first time")
        sz1 = os.stat(test_full_file).st_size
        db.execute()
        sz2 = os.stat(test_full_file).st_size
        self.failIf(sz2>sz1,"Command reexecuted second time")
        db.forceExecute()
        sz3 = os.stat(test_full_file).st_size
        self.failUnless(sz3>sz1,"Command did not force reexecute")

        #Test run deletes excess directories when, and only when, required
        os.mkdir(test_path + "/" + (today-timedelta(8)).isoformat())
        db.forceExecute()
        self.failIf(os.path.exists(test_path+"/"+(today-
            timedelta(8)).isoformat()),"Did not delete outdated directory")
        self.failUnless(os.path.exists(test_path+"/"+(today-
            timedelta(3)).isoformat()),"Deleted in-date directory")

        #Test log was actually created
        self.failUnless(os.path.exists(test_log), "Did not create log")


    def testLogBased(self):
        #Init object
        db = datebatch.DateBatcher()
        db.setUsingLog(test_path, 3, exceptionFunction, test_log)

        #Test run only runs when required        
        req = db.runRequired()
        self.failUnless(req,"Did not require run on clean directory")
        db.execute()
        req = db.runRequired()
        self.failUnless(req,"Did not require rerun after failure")
        db.setUsingLog(test_path, 3, testFunction, test_log)
        db.execute()
        req = db.runRequired()
        self.failIf(req,"Still required run after success")

        #Test run is executed when, and only when, it is required
        test_full_file = test_path+"/"+test_file
        self.failUnless(os.path.exists(test_full_file),
            "Command did not execute first time")
        sz1 = os.stat(test_full_file).st_size
        db.execute()
        sz2 = os.stat(test_full_file).st_size
        self.failIf(sz2>sz1,"Command reexecuted second time")
        db.forceExecute()
        sz3 = os.stat(test_full_file).st_size
        self.failUnless(sz3>sz1,"Command did not force reexecute")


if __name__ == "__main__": unittest.main()




#testLogMode