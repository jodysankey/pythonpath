import os
import tempfile
import unittest

import classifydir


class DateBatchTestCase(unittest.TestCase):

    def _rel_path(self, subdir_string):
        """Returns a path inside the test directory where each character in subdir_string
        defines a single letter subdirectory, e.g. _self_path(abc) = /tmp/UNIQUE_NAME/a/b/c."""
        path = self.test_dir.name
        for char in subdir_string:
            path = os.path.join(path, char)
        return path

    def _create_directories(self, subdir_strings):
        """Create all the directories supplied in one character per path segment form."""
        for path in [self._rel_path(s) for s in subdir_strings]:
            os.mkdir(path)

    def _create_classify(self, subdir_string, volume, protection,
                         recurse='true', compress='false', name=None):
        """Create a standard .classify file in the requested location."""
        lines = ['{}={}'.format(*tup) for tup in zip(
            ('volume', 'protection', 'recurse', 'compress'),
            (volume, protection, recurse, compress))]
        if name:
            lines.append('name={}'.format(name))
        self._create_raw_classify(subdir_string, lines)

    def _create_raw_classify(self, subdir_string, lines):
        """Create a .classify file containing the suppled lines in the requested location."""
        path = self._rel_path(subdir_string)
        with open(os.path.join(path, classifydir.MAGIC_FILE), 'w') as f:
            f.writelines(['{}\n'.format(l) for l in lines])

    def _create_files(self, subdir_string, sizes):
        """Create a set of text files of the requested sizes in the requested location. Files will
        be named with a sequential number starting at 1."""
        path = self._rel_path(subdir_string)
        for number, size in enumerate(sizes, start=1):
            with open(os.path.join(path, str(number)), 'w') as f:
                f.write("x" * size)

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory(prefix='classifydir_test_')
        self.test_subdir = os.path.split(self.test_dir.name)[1]

    def tearDown(self):
        self.test_dir.cleanup()


    def test_single_recursive_tree(self):
        self._create_directories(('a', 'ab', 'abc', 'd'))
        self._create_classify('', 'huge', 'secret', recurse='true', name='root')
        self._create_files('ab', (100, 200, 300))
        self._create_files('abc', (1000,))
        self._create_files('d', (20000,))

        cd = classifydir.ClassifiedDir(self.test_dir.name, fetch_info=True)

        # Test directory is the only root.
        self.assertTrue(cd.is_archive_root())
        self.assertEqual([d.name for d in cd.descendants()], ['root', 'a', 'b', 'c', 'd'])
        self.assertEqual([d.name for d in cd.descendant_members()], ['root', 'a', 'b', 'c', 'd'])
        self.assertEqual([d.name for d in cd.descendant_roots()], ['root'])
        self.assertEqual([d.name for d in cd.descendant_attenuations()], [])

        # With lots of properties.
        self.assertEqual(cd.total_size(), 21668) # includes the classify file.
        self.assertEqual(cd.total_file_count(), 6) # includes the classify file.
        self.assertEqual(cd.volume, 'huge')
        self.assertEqual(cd.protection, 'secret')
        self.assertEqual(cd.archive_size(), 21668)
        self.assertEqual(cd.archive_file_count(), 6)
        self.assertEqual(list(cd.archive_filenames()), [
            os.path.join(self.test_dir.name, '.classify'),
            os.path.join(self.test_dir.name, 'a', 'b', '1'),
            os.path.join(self.test_dir.name, 'a', 'b', '2'),
            os.path.join(self.test_dir.name, 'a', 'b', '3'),
            os.path.join(self.test_dir.name, 'a', 'b', 'c', '1'),
            os.path.join(self.test_dir.name, 'd', '1')])

        # Adding a file should change the hash and date
        with open(os.path.join(self._rel_path('d'), 'new'), 'w') as f:
            f.write("y" * 80)
        updated_cd = classifydir.ClassifiedDir(self.test_dir.name, fetch_info=True)
        self.assertEqual(updated_cd.archive_file_count(), 7)
        self.assertNotEqual(cd.archive_hash(), updated_cd.archive_hash())


    def test_single_tree_without_fetching(self):
        self._create_directories(('a', 'd'))
        self._create_classify('', 'large', 'secret', recurse='true', name='root')
        self._create_files('a', (100, 200, 300))
        self._create_files('d', (20000,))

        cd = classifydir.ClassifiedDir(self.test_dir.name, fetch_info=False)

        # If we don't fetch into many properties should be None, but the filenames still work.
        self.assertEqual([d.name for d in cd.descendants()], ['root', 'a', 'd'])
        self.assertEqual([d.name for d in cd.descendant_members()], ['root', 'a', 'd'])
        self.assertEqual([d.name for d in cd.descendant_roots()], ['root'])
        self.assertIsNone(cd.total_size())
        self.assertIsNone(cd.total_file_count())
        self.assertEqual(cd.volume, 'large')
        self.assertEqual(cd.protection, 'secret')
        self.assertIsNone(cd.archive_size())
        self.assertIsNone(cd.archive_file_count())
        self.assertIsNone(cd.archive_hash())
        self.assertEqual(list(cd.archive_filenames()), [
            os.path.join(self.test_dir.name, '.classify'),
            os.path.join(self.test_dir.name, 'a', '1'),
            os.path.join(self.test_dir.name, 'a', '2'),
            os.path.join(self.test_dir.name, 'a', '3'),
            os.path.join(self.test_dir.name, 'd', '1')])


    def test_sibling_archives(self):
        self._create_directories(('a', 'b', 'c', 'cd'))
        self._create_classify('a', 'small', 'restricted', recurse='true')
        self._create_classify('b', 'medium', 'confidential', recurse='true')
        self._create_classify('c', 'large', 'none', recurse='true')
        self._create_files('a', (100, 200))
        self._create_files('b', (2000,))
        self._create_files('c', (30000,))

        cd = classifydir.ClassifiedDir(self.test_dir.name, fetch_info=True)

        # Test directory is not itself a root.
        self.assertFalse(cd.is_archive_root())
        self.assertEqual([d.name for d in cd.descendants()], [self.test_subdir, 'a', 'b', 'c', 'd'])
        self.assertEqual(cd.total_size(), 32486) # includes the classify files.
        self.assertEqual(cd.total_file_count(), 7) # includes the classify files.

        # But should contain three roots.
        roots = list(cd.descendant_roots())
        self.assertEqual([d.name for d in roots], ['a', 'b', 'c'])
        for root in roots:
            self.assertTrue(root.is_archive_root())

        # With lots of properties.
        self.assertEqual(roots[0].archive_size(), 363)
        self.assertEqual(roots[0].total_file_count(), 3)
        self.assertEqual(roots[0].volume, 'small')
        self.assertEqual(roots[0].protection, 'restricted')
        self.assertEqual([d.name for d in roots[0].descendants()], ['a'])

        self.assertEqual(roots[1].archive_size(), 2066)
        self.assertEqual(roots[1].total_file_count(), 2)
        self.assertEqual(roots[1].volume, 'medium')
        self.assertEqual(roots[1].protection, 'confidential')
        self.assertEqual([d.name for d in roots[1].descendants()], ['b'])

        self.assertEqual(roots[2].archive_size(), 30057)
        self.assertEqual(roots[2].total_file_count(), 2)
        self.assertEqual(roots[2].volume, 'large')
        self.assertEqual(roots[2].protection, 'none')
        self.assertEqual([d.name for d in roots[2].descendants()], ['c', 'd'])


    def test_archives_inside_non_recursive(self):
        self._create_directories(('a', 'ab', 'c'))
        self._create_classify('', 'small', 'restricted', recurse='false', name='root')
        self._create_classify('a', 'small', 'confidential', recurse='true')
        self._create_classify('c', 'none', 'none', recurse='true')
        self._create_files('', (100, 200))
        self._create_files('ab', (1000,))
        self._create_files('c', (20000,))

        cd = classifydir.ClassifiedDir(self.test_dir.name, fetch_info=True)

        # Test directory should have one child root (volume=none gets ignored) but since its not
        # recursive these should not be considered members.
        self.assertTrue(cd.is_archive_root())
        self.assertEqual([d.name for d in cd.descendants()], ['root', 'a', 'b', 'c'])
        self.assertEqual([d.name for d in cd.descendant_members()], ['root'])
        self.assertEqual([d.name for d in cd.descendant_roots()], ['root', 'a'])

        # Root totals include all files but the archive shouldn't include files in subdirectories.
        self.assertEqual(cd.total_size(), 21495)
        self.assertEqual(cd.total_file_count(), 7)
        self.assertEqual(cd.archive_size(), 374)
        self.assertEqual(cd.archive_file_count(), 3)
        self.assertEqual(list(cd.archive_filenames()), [
            os.path.join(self.test_dir.name, '.classify'),
            os.path.join(self.test_dir.name, '1'),
            os.path.join(self.test_dir.name, '2')])

        # The lower level archive should include its own files.
        child = list(cd.descendant_roots())[1]
        self.assertTrue(child.is_archive_root())
        self.assertEqual(child.total_size(), 1065)
        self.assertEqual(child.total_file_count(), 2)
        self.assertEqual(child.archive_size(), 1065)
        self.assertEqual(child.archive_file_count(), 2)
        self.assertEqual(list(child.archive_filenames()), [
            os.path.join(self.test_dir.name, 'a', '.classify'),
            os.path.join(self.test_dir.name, 'a', 'b', '1')])


    def test_missing_classify_in_non_recursive(self):
        self._create_directories(('a', 'b'))
        self._create_classify('', 'small', 'restricted', recurse='false', name='root')
        self._create_classify('a', 'small', 'confidential', recurse='true')
        # Note: no classify in b, this is an error!
        with self.assertRaises(Exception):
            classifydir.ClassifiedDir(self.test_dir.name, fetch_info=True)


    def test_override_archives_inside_recursive_archive(self):
        self._create_directories(('a', 'ab', 'c', 'cd', 'e'))
        self._create_classify('', 'small', 'restricted', recurse='true', name='root')
        # Note this overrides a directory inside the recursive parent.
        self._create_classify('a', 'small', 'confidential', recurse='true')
        # Note this ceases archiving inside the recursive parent.
        self._create_classify('c', 'none', 'none', recurse='true')
        # Note this tries to restart archiving in a subdirectory with a different name.
        self._create_classify('cd', 'medium', 'restricted', recurse='true')
        self._create_files('', (100, 200))
        self._create_files('a', (10000,))
        self._create_files('ab', (20000,))
        self._create_files('c', (1000,))
        self._create_files('cd', (2000,))
        self._create_files('e', (5000,))

        cd = classifydir.ClassifiedDir(self.test_dir.name, fetch_info=True)

        self.assertTrue(cd.is_archive_root())
        self.assertEqual([d.name for d in cd.descendants()], ['root', 'a', 'b', 'c', 'd', 'e'])
        # Members should not include the overridden directory or the attenuated directory.
        self.assertEqual([d.name for d in cd.descendant_members()], ['root', 'e'])
        self.assertEqual([d.name for d in cd.descendant_roots()], ['root', 'a', 'd'])
        self.assertEqual([d.name for d in cd.descendant_attenuations()], ['c'])

        # Root totals include all files but the archive shouldn't include files in the overridden
        # directory.
        self.assertEqual(cd.total_size(), 38558)
        self.assertEqual(cd.total_file_count(), 11)
        self.assertEqual(cd.archive_size(), 5373)
        self.assertEqual(cd.archive_file_count(), 4)
        self.assertEqual(list(cd.archive_filenames()), [
            os.path.join(self.test_dir.name, '.classify'),
            os.path.join(self.test_dir.name, '1'),
            os.path.join(self.test_dir.name, '2'),
            os.path.join(self.test_dir.name, 'e', '1')])

        # The lower level archives should include thier own files.
        child = list(cd.descendant_roots())[1]
        self.assertTrue(child.is_archive_root())
        self.assertEqual(child.total_size(), 30065)
        self.assertEqual(child.total_file_count(), 3)
        self.assertEqual(child.archive_size(), 30065)
        self.assertEqual(child.archive_file_count(), 3)
        self.assertEqual(list(child.archive_filenames()), [
            os.path.join(self.test_dir.name, 'a', '.classify'),
            os.path.join(self.test_dir.name, 'a', '1'),
            os.path.join(self.test_dir.name, 'a', 'b', '1')])

        # The lower level archives should include thier own files.
        child = list(cd.descendant_roots())[2]
        self.assertTrue(child.is_archive_root())
        self.assertEqual(child.archive_size(), 2064)
        self.assertEqual(child.archive_file_count(), 2)
        self.assertEqual(list(child.archive_filenames()), [
            os.path.join(self.test_dir.name, 'c', 'd', '.classify'),
            os.path.join(self.test_dir.name, 'c', 'd', '1')])


    def test_parse_with_comments(self):
        self._create_raw_classify('', [
            '# Test file with some comments',
            '   # Some not at the start',
            'volume=small',
            'protection=none # Comments allowed after text',
            'recurse=true',
            'compress=true'])
        classifydir.ClassifiedDir(self.test_dir.name, fetch_info=True)


    def test_parse_fails_missing_parameter(self):
        self._create_raw_classify('', [
            'volume=small',
            'recurse=true',
            'compress=true'])
        with self.assertRaises(Exception):
            classifydir.ClassifiedDir(self.test_dir.name, fetch_info=True)


    def test_parse_fails_duplicate_parameter(self):
        self._create_raw_classify('', [
            'volume=small',
            'protection=restricted',
            'protection=restricted',
            'recurse=true',
            'compress=true'])
        with self.assertRaises(Exception):
            classifydir.ClassifiedDir(self.test_dir.name, fetch_info=True)


    def test_parse_fails_unknown_parameter(self):
        self._create_raw_classify('', [
            'volume=small',
            'protection=restricted',
            'mystery=what_am_i',
            'recurse=true',
            'compress=true'])
        with self.assertRaises(Exception):
            classifydir.ClassifiedDir(self.test_dir.name, fetch_info=True)


    def test_parse_fails_invalid_value(self):
        self._create_raw_classify('', [
            'volume=small',
            'protection=super_dooper_spicy_secret',
            'recurse=true',
            'compress=true'])
        with self.assertRaises(Exception):
            classifydir.ClassifiedDir(self.test_dir.name, fetch_info=True)


    def test_parse_fails_malformed_line(self):
        self._create_raw_classify('', [
            'volume='
            'protection=none'
            'recurse=true'
            'compress=true'])
        with self.assertRaises(Exception):
            classifydir.ClassifiedDir(self.test_dir.name, fetch_info=False)


if __name__ == "__main__":
    unittest.main()
