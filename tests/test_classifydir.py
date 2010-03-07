import classifydir
import os
import shutil
import unittest
import platform

if platform.system()=='Windows':
    #test_path = os.getenv("TMP") + "/DateBatchTest" # TMP set to some hideous directory
    test_path = r"C:\Temp\ClassifyDirTest"
else:
    test_path = "/tmp/ClassifyDirTest"
    

def createClassify(subpath,volume,protection,recurse):
    """Create a standard .classify file at given location"""

    path = test_path
    for subdir in subpath:
        path = os.path.join(path,subdir)
    file = open(os.path.join(path,classifydir.MAGIC_FILE),"a+")
    for setting in zip(('volume','protection','recurse'),(volume,protection,recurse)):
        file.write("{}={}\n".format(*setting))
    file.close()

def createFile(subpath,name,size):
    """Create a standard text file of given size at given location"""

    path = test_path
    for subdir in subpath:
        path = os.path.join(path,subdir)
    file = open(os.path.join(path,name),"a+")
    file.write("x"*size)
    file.close()



class DateBatchTestCase(unittest.TestCase):

    def setUp(self):
        #Make sure we remove any existing test dir first, then create a new one
#        if platform.system()=='Windows':
#
#        try:
#            os.stat(test_path)
#        except WindowsError:
#            pass
#        else:
#            shutil.rmtree(test_path)
        if os.path.isdir(test_path):
            shutil.rmtree(test_path)
        os.mkdir(test_path)

        # Now create a directory structure which looks like this
            
        #            Test 1  Test 2  Test 3  Test 4
        # +            -      N,n      -       -
        # +-A          -      R,n     Sm,n    Sm,R
        # | +-B        -      C,n      -       -
        # | | \-C     Sm,R    S,n      -      Me,R
        # | \-D       Me,n    S,R      -       -
        # |   +-E     Lg,R     -       -       -
        # +-F         Hu,R    S,R      -       -
        # \-G         No,R    S,R      -       -

        for subpath in ('a','ab','abc','ad','ade','f','g'):
            path = test_path
            for subdir in subpath:
                path = os.path.join(path,subdir)
            os.mkdir(path)
                

    def testStructureOne (self):
        """Test all sizes, one and two levels undefined, recurse in non recurse"""
        createClassify('abc','small','none','true')
        createClassify('ad','medium','none','false')
        createClassify('ade','small','none','true')
        createClassify('f','huge','none','true')
        createClassify('g','none','none','true')

        target = [
                  ['small', 'none', 'a:b:c'], 
                  ['medium', 'none', 'a:d'], 
                  ['small', 'none', 'a:d:e'], 
                  ['huge', 'none', 'f'], 
                  ['none', 'none', 'g']
                ]
        for x in range(len(target)):
            target[x][2] = target[x][2].replace(':',os.sep)

        cd = classifydir.ClassifiedDir(test_path,True)
        result = cd.dirList()
        print(target)
        print(result)
        
        self.failUnlessEqual(result,target,"Structure 1 - Did not return correct list")

        #Also just run the functions to verify no exceptions
        cd.printSummary()


    def testStructureTwo (self):
        """Test all protections, no levels undefined, multi level non recurse"""
        createClassify('','none','none','false')
        createClassify('a','none','restricted','false')
        createClassify('ab','none','confidential','false')
        createClassify('abc','none','secret','false')
        createClassify('ad','none','secret','true')
        createClassify('f','none','secret','true')
        createClassify('g','none','secret','true')

        target = [
                  ['none', 'none', ''], 
                  ['none', 'restricted', 'a'], 
                  ['none', 'confidential', 'a:b'], 
                  ['none', 'secret', 'a:b:c'], 
                  ['none', 'secret', 'a:d'], 
                  #['none', 'secret', 'a:d:e'], 
                  ['none', 'secret', 'f'], 
                  ['none', 'secret', 'g']
                ]
        for x in range(len(target)):
            target[x][2] = target[x][2].replace(':',os.sep)

        cd = classifydir.ClassifiedDir(test_path,False)
        result = cd.dirList()
        print(target)
        print(result)
        
        self.failUnlessEqual(result,target,"Structure 2 - Did not return correct list")

        #Also just run some functions to verify no exceptions
        cd.printSummary()



    def testStructureThree (self):
        """Test not specifying underneath non-recursive is failure"""
        createClassify('a','small','restricted','false')

        with self.assertRaises(Exception):
            classifydir.ClassifiedDir(test_path,True)


    def testStructureFour (self):
        """Test specifying underneath recursive is failure"""
        createClassify('a','small','restricted','true')
        createClassify('abc','medium','restricted','true')

        with self.assertRaises(Exception):
            classifydir.ClassifiedDir(test_path,True)


    def testBadClassifyComment (self):
        """Test comments work in .classify"""        
        file = open(os.path.join(test_path,classifydir.MAGIC_FILE),"a+")
        file.write("# Single line comment\n")
        file.write("   # Single line comment not at start\n")
        file.write("volume=small #Line comment\nprotection=none\nrecurse=true\n")
        file.close()

        classifydir.ClassifiedDir(test_path,True)


    def testBadClassifyOne (self):
        """Test missing parameter in .classify"""        
        file = open(os.path.join(test_path,classifydir.MAGIC_FILE),"a+")
        file.write("protection=none\nrecurse=true\n")
        file.close()

        with self.assertRaises(Exception):
            classifydir.ClassifiedDir(test_path)
 

    def testBadClassifyTwo (self):
        """Test duplicate parameter in .classify"""        
        file = open(os.path.join(test_path,classifydir.MAGIC_FILE),"a+")
        file.write("volume=none\nprotection=none\nvolume=small\nrecurse=true\n")
        file.close()

        with self.assertRaises(Exception):
            classifydir.ClassifiedDir(test_path)


    def testBadClassifyThree (self):
        """Test bad setting in .classify"""        
        file = open(os.path.join(test_path,classifydir.MAGIC_FILE),"a+")
        file.write("vollume=none\nprotection=none\nrecurse=true\n")
        file.close()

        with self.assertRaises(Exception):
            classifydir.ClassifiedDir(test_path)


    def testBadClassifyFour (self):
        """Test bad value in .classify"""        
        file = open(os.path.join(test_path,classifydir.MAGIC_FILE),"a+")
        file.write("volume=moderate\nprotection=none\nrecurse=true\n")
        file.close()

        with self.assertRaises(Exception):
            classifydir.ClassifiedDir(test_path)


    def testBadClassifyFive (self):
        """Test malformed line in .classify"""        
        file = open(os.path.join(test_path,classifydir.MAGIC_FILE),"a+")
        file.write("volume=\nprotection=none\nrecurse=true\n")
        file.close()

        with self.assertRaises(Exception):
            classifydir.ClassifiedDir(test_path)

        

if __name__ == "__main__": unittest.main()


