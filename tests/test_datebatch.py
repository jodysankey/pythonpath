#!/usr/bin/python3

from datetime import date, datetime, timedelta
import os
import tempfile
import unittest

import datebatch

TEST_FILE = "test.txt"

def test_function(root_dir):
    """Function suitable for datebatch use. Adds a date line to test_file"""
    exclusion_file = open(root_dir + "/" + TEST_FILE, "a+")
    exclusion_file.write("Ran test function " + datetime.now().isoformat() + "\n")
    exclusion_file.close()

def exception_function(root_dir):
    """Function suitable for datebatch use. Throws an exception"""
    raise AttributeError


class DateBatchTestCase(unittest.TestCase):
    """Tests for the DateBatcher class."""

    def setUp(self):
        self.output_dir = tempfile.TemporaryDirectory()
        self.output_path = self.output_dir.name
        self.log_path = os.path.join(self.output_path, "test.log")
        self.today = date.today()

    def tearDown(self):
        self.output_dir.cleanup()
        return super().tearDown()

    def date_string(self, delta_days):
        """Returns a ISO date string the specified number of days after today."""
        return (self.today + timedelta(delta_days)).isoformat()

    def test_initialization_requirement(self):
        date_batcher = datebatch.DateBatcher(None, 1, 1, None, None, None)
        self.assertRaises(AttributeError, date_batcher.run_required)
        self.assertRaises(AttributeError, date_batcher.force_execute)
        self.assertRaises(AttributeError, date_batcher.execute)

    def test_function_exception(self):
        date_batcher = datebatch.DateBatcher.using_dir(self.output_path, 1, 1, exception_function)
        date_batcher.execute()
        self.assertTrue(date_batcher.run_required(), "Did not require rerun following failure")

    def test_dir_based_without_log(self):
        # Init object
        date_batcher = datebatch.DateBatcher.using_dir(self.output_path, 3, 2, test_function)

        # Test run required returns appropriate values
        req = date_batcher.run_required()
        self.assertTrue(req, "Did not require run on empty directory")
        os.mkdir(os.path.join(self.output_path, self.date_string(-3)))
        req = date_batcher.run_required()
        self.assertTrue(req, "Did not require run on out of date directory")
        date_batcher = datebatch.DateBatcher.using_dir(self.output_path, 4, 2, test_function)
        req = date_batcher.run_required()
        self.assertFalse(req, "Required run on in-date directory")

        # Test with log continues to test more complex conditions


    def test_dir_based_with_log(self):
        # Init object
        date_batcher = datebatch.DateBatcher.using_dir(
            self.output_path, 3, 2, test_function, self.log_path)

        # Test run required returns appropriate values
        req = date_batcher.run_required()
        self.assertTrue(req, "Did not require run on empty directory")
        os.mkdir(os.path.join(self.output_path, self.date_string(-3)))
        req = date_batcher.run_required()
        self.assertTrue(req, "Did not require run on out of date directory")
        date_batcher.spacing = 5
        req = date_batcher.run_required()
        self.assertFalse(req, "Required run on in-date directory")

        # Test run is executed when, and only when, it is required
        date_batcher.spacing = 3
        test_full_file = os.path.join(self.output_path, self.date_string(0), TEST_FILE)
        date_batcher.execute()
        self.assertTrue(os.path.exists(test_full_file),
                        "Command did not execute first time")
        sz1 = os.stat(test_full_file).st_size
        date_batcher.execute()
        sz2 = os.stat(test_full_file).st_size
        self.assertFalse(sz2 > sz1, "Command reexecuted second time")
        date_batcher.force_execute()
        sz3 = os.stat(test_full_file).st_size
        self.assertTrue(sz3 > sz1, "Command did not force reexecute")

        # Test run deletes excess directories when, and only when, required
        os.mkdir(os.path.join(self.output_path, self.date_string(-8)))
        date_batcher.force_execute()
        self.assertFalse(os.path.exists(os.path.join(self.output_path, self.date_string(-8))),
                         "Did not delete outdated directory")
        self.assertTrue(os.path.exists(os.path.join(self.output_path, self.date_string(-3))),
                        "Deleted in-date directory")

        # Test log was actually created
        self.assertTrue(os.path.exists(self.log_path), "Did not create log")


    def test_log_based(self):
        # Init object
        date_batcher = datebatch.DateBatcher.using_log(
            self.output_path, 3, exception_function, self.log_path)

        # Test run only runs when required
        self.assertTrue(date_batcher.run_required(), "Did not require run on clean directory")
        date_batcher.execute()
        self.assertTrue(date_batcher.run_required(), "Did not require rerun after failure")
        date_batcher.function = test_function
        date_batcher.execute()
        self.assertFalse(date_batcher.run_required(), "Still required run after success")

        # Test run is executed when, and only when, it is required
        test_full_file = os.path.join(self.output_path, TEST_FILE)
        self.assertTrue(os.path.exists(test_full_file),
                        "Command did not execute first time")
        sz1 = os.stat(test_full_file).st_size
        date_batcher.execute()
        sz2 = os.stat(test_full_file).st_size
        self.assertFalse(sz2 > sz1, "Command reexecuted second time")
        date_batcher.force_execute()
        sz3 = os.stat(test_full_file).st_size
        self.assertTrue(sz3 > sz1, "Command did not force reexecute")


if __name__ == "__main__":
    unittest.main()
