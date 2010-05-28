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
    

def createClassify(subpath,volume,protection,recurse,compress,name=''):
    """Create a standard .classify file at given location"""

    path = test_path
    for subdir in subpath:
        path = os.path.join(path,subdir)
    file = open(os.path.join(path,classifydir.MAGIC_FILE),"a+")
    for setting in zip(('volume','protection','recurse','compress'),(volume,protection,recurse,compress)):
        file.write("{}={}\n".format(*setting))
    if len(name)>0:
        file.write("name={}\n".format(name))
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
        if os.path.isdir(test_path):
            shutil.rmtree(test_path)
        os.mkdir(test_path)

        # Now create a directory structure which looks like this
        # * Indicates compressible
            
        #            Test 1  Test 2  Test 3  Test 4
        # +            -      N,n      -       -
        # +-A          -      R,n *   Sm,n    Sm,R
        # | +-B        -      C,n *    -       -
        # | | \-C     Sm,R    S,n *    -      Me,R
        # | \-D       Me,n    S,R      -       -
        # |   +-E     Lg,R     -       -       -
        # +-F         Hu,R    R,R      -       -
        # \-G         No,R    S,R      -       -

        for subpath in ('a','ab','abc','ad','ade','f','g'):
            path = test_path
            for subdir in subpath:
                path = os.path.join(path,subdir)
            os.mkdir(path)
                

    def testStructureOne (self):
        """Test all sizes, one and two levels undefined, recurse in non recurse"""
        createClassify('abc','small','none','true','false')
        createClassify('ad','medium','none','false','false')
        createClassify('ade','large','none','true','false')
        createClassify('f','huge','none','true','false')
        createClassify('g','none','none','true','false')

        createFile('ab', 'none', 500)
        createFile('abc', 'small1', 500)
        createFile('abc', 'small2', 500)
        createFile('ad', 'medium', 500)
        createFile('ade', 'large', 500)
        createFile('f', 'huge', 500)

        target = [
                  ['small', 'none', False, 'a:b:c', 'c'], 
                  ['medium', 'none', False, 'a:d', 'd'], 
                  ['large', 'none', False,'a:d:e', 'e'], 
                  ['huge', 'none', False, 'f', 'f'], 
                  ['none', 'none', False, 'g', 'g']
                ]
        for x in range(len(target)):
            target[x][3] = target[x][3].replace(':',os.sep)

        cd = classifydir.ClassifiedDir(test_path,True)
        result = cd.dirList()
        print()
        print("Target: ",target)
        print("Result: ",result)
        
        self.failUnlessEqual(result,target,"Structure 1 - Did not return correct list")

        self.failUnless(cd.dirCount()==5,
                        "Structure 1 - Returned wrong total directory count")
        self.failUnless(cd.dirCount('small',None)==1,
                        "Structure 1 - Returned wrong small directory count")
        self.failUnless(cd.fileCount()==10,
                        "Structure 1 - Returned wrong total file count")
        self.failUnless(cd.fileCount('medium',None)==2,
                        "Structure 1 - Returned wrong medium file count")
        
        # Need two different size for windows/unix classify line endings
        self.failUnless(cd.totalSize()==2805 or cd.totalSize()==2785,
                        "Structure 1 - Returned wrong total files size")
        self.failUnless(cd.totalSize('large','secret')==0,
                        "Structure 1 - Returned wrong large secret file size")


        #Also just run the functions to verify no exceptions
        cd.printSummary()
        cd.printTable()


    def testStructureTwo (self):
        """Test all protections, no levels undefined, multi level non recurse"""
        createClassify('','none','none','false','false')
        createClassify('a','none','restricted','false','true','named_a')
        createClassify('ab','none','confidential','false','true')
        createClassify('abc','none','secret','false','true')
        createClassify('ad','none','secret','true','false')
        createClassify('f','none','restricted','true','false','named_f')
        createClassify('g','none','secret','true','false')

        target = [
                  ['none', 'none', False, '', ''], 
                  ['none', 'restricted', True, 'a', 'named_a'], 
                  ['none', 'confidential', True, 'a:b', 'b'], 
                  ['none', 'secret', True, 'a:b:c', 'c'], 
                  ['none', 'secret', False, 'a:d', 'd'], 
                  #['none', 'secret', False, 'a:d:e'], 
                  ['none', 'restricted', False, 'f', 'named_f'], 
                  ['none', 'secret', False, 'g', 'g']
                ]
        for x in range(len(target)):
            target[x][3] = target[x][3].replace(':',os.sep)

        cd = classifydir.ClassifiedDir(test_path,False)
        result = cd.dirList()
        print()
        print("Target: ",target)
        print("Result: ",result)
        
        self.failUnlessEqual(result,target,"Structure 2 - Did not return correct list (incl names)")

        cds = cd.classDirList(None,None)
        self.failUnless(len(cds)==7,"Structure 2 - Return wrong number of classified directory objects")

        self.failUnless(cds[0].preferredMechanism()=='zip',"Structure 2 - Returned wrong mechanism for zip directory 1")
        self.failUnless(cds[1].preferredMechanism()=='zip',"Structure 2 - Returned wrong mechanism for zip directory 2")
        self.failUnless(cds[4].preferredMechanism()=='jxx',"Structure 2 - Returned wrong mechanism for jxx directory")
        self.failUnless(cds[5].preferredMechanism()=='copy',"Structure 2 - Returned wrong mechanism for copy directory")
        
        
        #Also just run some functions to verify no exceptions
        cd.printSummary()
        cd.printTable()



    def testStructureThree (self):
        """Test not specifying underneath non-recursive is failure"""
        createClassify('a','small','restricted','false','false')

        with self.assertRaises(Exception):
            classifydir.ClassifiedDir(test_path,True)


    def testStructureFour (self):
        """Test specifying underneath recursive is failure"""
        createClassify('a','small','restricted','true','false')
        createClassify('abc','medium','restricted','true','false')

        with self.assertRaises(Exception):
            classifydir.ClassifiedDir(test_path,True)


    def testClassifyComment (self):
        """Test comments work in .classify"""        
        file = open(os.path.join(test_path,classifydir.MAGIC_FILE),"a+")
        file.write("# Single line comment\n")
        file.write("   # Single line comment not at start\n")
        file.write("volume=small #Line comment\nprotection=none\nrecurse=true\ncompress=true\n")
        file.close()

        classifydir.ClassifiedDir(test_path,True)


    def testBadClassifyOne (self):
        """Test missing parameter in .classify"""        
        file = open(os.path.join(test_path,classifydir.MAGIC_FILE),"a+")
        file.write("protection=none\nrecurse=true\ncompress=false\n")
        file.close()

        with self.assertRaises(Exception):
            classifydir.ClassifiedDir(test_path)
 

    def testBadClassifyTwo (self):
        """Test duplicate parameter in .classify"""        
        file = open(os.path.join(test_path,classifydir.MAGIC_FILE),"a+")
        file.write("volume=none\nprotection=none\nvolume=small\nrecurse=true\ncompress=true\n")
        file.close()

        with self.assertRaises(Exception):
            classifydir.ClassifiedDir(test_path)


    def testBadClassifyThree (self):
        """Test bad setting in .classify"""        
        file = open(os.path.join(test_path,classifydir.MAGIC_FILE),"a+")
        file.write("vollume=none\nprotection=none\nrecurse=true\ncompress=false\n")
        file.close()

        with self.assertRaises(Exception):
            classifydir.ClassifiedDir(test_path)


    def testBadClassifyFour (self):
        """Test bad value in .classify"""        
        file = open(os.path.join(test_path,classifydir.MAGIC_FILE),"a+")
        file.write("volume=moderate\nprotection=none\nrecurse=true\ncompress=false\n")
        file.close()

        with self.assertRaises(Exception):
            classifydir.ClassifiedDir(test_path)


    def testBadClassifyFive (self):
        """Test malformed line in .classify"""        
        file = open(os.path.join(test_path,classifydir.MAGIC_FILE),"a+")
        file.write("volume=\nprotection=none\nrecurse=true\ncompress=true\n")
        file.close()

        with self.assertRaises(Exception):
            classifydir.ClassifiedDir(test_path)

        

if __name__ == "__main__": 
    
    # This way of running allows quick focus on a particular test by entering the number, or all
    # tests by just entering "test" 
    ldr = unittest.TestLoader()
    
    #ldr.testMethodPrefix = "testStructureOne"
    ldr.testMethodPrefix = "test"
    
    suite = ldr.loadTestsFromTestCase(DateBatchTestCase)
    unittest.TextTestRunner(verbosity=2).run(suite)


