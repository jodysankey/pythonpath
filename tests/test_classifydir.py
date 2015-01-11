import classifydir
import os
import shutil
import unittest
import platform
from pickle import _getattribute


if platform.system()=='Windows':
    #test_path = os.getenv("TMP") + "/DateBatchTest" # TMP set to some hideous directory
    test_path = r"C:\Temp\ClassifyDirTest"
else:
    test_path = "/tmp/ClassifyDirTest"
    

def _createClassify(subpath, volume, protection, recurse, compress, name=''):
    """Create a standard .classify exclusion_file at given location"""
    path = test_path
    for subdir in subpath:
        path = os.path.join(path,subdir)
    exclusion_file = open(os.path.join(path,classifydir.MAGIC_FILE),"a+")
    for setting in zip(('volume','protection','recurse','compress'),(volume,protection,recurse,compress)):
        exclusion_file.write("{}={}\n".format(*setting))
    if len(name):
        exclusion_file.write("name={}\n".format(name))
    exclusion_file.close()

def _createFile(subpath,name,size):
    """Create a standard text exclusion_file of given size at given location"""
    path = test_path
    for subdir in subpath:
        path = os.path.join(path,subdir)
    exclusion_file = open(os.path.join(path,name),"a+")
    exclusion_file.write("x"*size)
    exclusion_file.close()
        
def _getAttributeTuple(cd):
    """Returns a standard tuple of attributes used to verify a classdir"""
    return (cd.volume, cd.protection, cd.compress, cd.rel_path, cd.name)




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
        _createClassify('abc','small','none','true','false')
        _createClassify('ad','medium','none','false','false')
        _createClassify('ade','large','none','true','false')
        _createClassify('f','huge','none','true','false')
        _createClassify('g','none','none','true','false')

        _createFile('ab', 'none', 500)
        _createFile('abc', 'small1', 500)
        _createFile('abc', 'small2', 500)
        _createFile('ad', 'medium', 500)
        _createFile('ade', 'large', 500)
        _createFile('f', 'huge', 500)

        expected_dirs = [
            ('small', 'none', False, os.path.join('a','b','c'), 'c'), 
            ('medium', 'none', False, os.path.join('a','d'), 'd'), 
            ('large', 'none', False, os.path.join('a','d','e'), 'e'), 
            ('huge', 'none', False, 'f', 'f'), 
        ]

        cd = classifydir.ClassifiedDir(test_path, '', fetch_info=True)
        result_dirs = [_getAttributeTuple(child) for child in cd.descendants()
                       if child.archiveRoot() != None]
        #print("Target1: ", expected_dirs)
        #print("Result1: ", result_dirs)
        
        self.assertEqual(result_dirs, expected_dirs, "Directory list")
        self.assertEqual(cd.totalFileCount(), 11, "Total file count")
        # Need two different size for windows/unix classify line endings
        self.assertIn(cd.totalSize(), (3305,  3285), "Total files size")

        expected_archives = [
            ('small', 'none', False, os.path.join('a','b','c'), 'c'), 
            ('medium', 'none', False, os.path.join('a','d'), 'd'), 
            ('large', 'none', False, os.path.join('a','d','e'), 'e'), 
            ('huge', 'none', False, 'f', 'f'), 
        ]

        result_archives = [_getAttributeTuple(arc) for arc in cd.descendants(archives_only=True)]
        self.assertEqual(result_archives, expected_archives, "Archive list")


    def testStructureTwo (self):
        """Test all protections, no levels undefined, multi level non recurse"""
        _createClassify('','small','none','false','false')
        _createClassify('a','small','restricted','false','true','named_a')
        _createClassify('ab','small','confidential','false','true')
        _createClassify('abc','small','secret','false','true')
        _createClassify('ad','small','secret','true','false')
        _createClassify('f','small','restricted','true','false','named_f')
        _createClassify('g','small','secret','true','false')

        expected_dirs = [
            ('small', 'none', False, '', ''), 
            ('small', 'restricted', True, 'a', 'named_a'), 
            ('small', 'confidential', True, os.path.join('a','b'), 'b'), 
            ('small', 'secret', True, os.path.join('a','b','c'), 'c'), 
            ('small', 'secret', False, os.path.join('a','d'), 'd'), 
            ('small', 'secret', False, os.path.join('a','d','e'), 'e'), 
            ('small', 'restricted', False, 'f', 'named_f'), 
            ('small', 'secret', False, 'g', 'g')
          ]

        cd = classifydir.ClassifiedDir(test_path, '', fetch_info=True)
        result_dirs = [_getAttributeTuple(child) for child in cd.descendants()]
        #print("Target2: ", expected_dirs)
        #print("Result2: ", result_dirs)
        self.assertEqual(result_dirs, expected_dirs, "Directory list")

        expected_archives = [
            ('small', 'none', False, '', ''), 
            ('small', 'restricted', True, 'a', 'named_a'), 
            ('small', 'confidential', True, os.path.join('a','b'), 'b'), 
            ('small', 'secret', True, os.path.join('a','b','c'), 'c'), 
            ('small', 'secret', False, os.path.join('a','d'), 'd'), 
            ('small', 'restricted', False, 'f', 'named_f'), 
            ('small', 'secret', False, 'g', 'g')
          ]

        result_archives = [_getAttributeTuple(arc) for arc in cd.descendantRoots()]
        self.assertEqual(result_archives, expected_archives, "Archive list")


    def testStructureThree (self):
        """Test not specifying underneath non-recursive is failure"""
        _createClassify('a','small','restricted','false','false')

        with self.assertRaises(Exception):
            classifydir.ClassifiedDir(test_path,True)


    def testStructureFour (self):
        """Test specifying underneath recursive is failure"""
        _createClassify('a','small','restricted','true','false')
        _createClassify('abc','medium','restricted','true','false')

        with self.assertRaises(Exception):
            classifydir.ClassifiedDir(test_path,True)


    def testClassify_validComment(self):
        """Test comments work in .classify"""        
        exclusion_file = open(os.path.join(test_path,classifydir.MAGIC_FILE),"a+")
        exclusion_file.write("# Single line comment\n")
        exclusion_file.write("   # Single line comment not at start\n")
        exclusion_file.write("volume=small #Line comment\nprotection=none\nrecurse=true\ncompress=true\n")
        exclusion_file.close()

        classifydir.ClassifiedDir(test_path, '', fetch_info=False)


    def testClassify_missingParameter(self):
        """Test missing parameter in .classify"""        
        exclusion_file = open(os.path.join(test_path,classifydir.MAGIC_FILE),"a+")
        exclusion_file.write("protection=none\nrecurse=true\ncompress=false\n")
        exclusion_file.close()

        with self.assertRaises(Exception):
            classifydir.ClassifiedDir(test_path, '', fetch_info=False)
 

    def testClassify_duplicateParameter(self):
        """Test duplicate parameter in .classify"""        
        exclusion_file = open(os.path.join(test_path, classifydir.MAGIC_FILE),"a+")
        exclusion_file.write("volume=none\nprotection=none\nvolume=small\nrecurse=true\ncompress=true\n")
        exclusion_file.close()

        with self.assertRaises(Exception):
            classifydir.ClassifiedDir(test_path, '', fetch_info=False)


    def testClassify_unknownSetting(self):
        """Test bad setting in .classify"""        
        exclusion_file = open(os.path.join(test_path, classifydir.MAGIC_FILE),"a+")
        exclusion_file.write("vollume=none\nprotection=none\nrecurse=true\ncompress=false\n")
        exclusion_file.close()

        with self.assertRaises(Exception):
            classifydir.ClassifiedDir(test_path, '', fetch_info=False)


    def testClassify_illegalSettingValue(self):
        """Test bad value in .classify"""        
        exclusion_file = open(os.path.join(test_path,classifydir.MAGIC_FILE),"a+")
        exclusion_file.write("volume=moderate\nprotection=none\nrecurse=true\ncompress=false\n")
        exclusion_file.close()

        with self.assertRaises(Exception):
            classifydir.ClassifiedDir(test_path, '', fetch_info=True)


    def testClassify_malformedLine(self):
        """Test malformed line in .classify"""        
        exclusion_file = open(os.path.join(test_path,classifydir.MAGIC_FILE),"a+")
        exclusion_file.write("volume=\nprotection=none\nrecurse=true\ncompress=true\n")
        exclusion_file.close()

        with self.assertRaises(Exception):
            classifydir.ClassifiedDir(test_path, '', fetch_info=False)


if __name__ == "__main__": 
    
    # This way of running allows quick focus on a particular test by entering the number, or all
    # tests by just entering "test" 
    ldr = unittest.TestLoader()
    
    ldr.testMethodPrefix = "test"
    
    suite = ldr.loadTestsFromTestCase(DateBatchTestCase)
    unittest.TextTestRunner(verbosity=2).run(suite)


