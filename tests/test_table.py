#!/usr/bin/python3

from table import Cell, Table
import unittest
import io
from numpy.ma.testutils import assert_equal

RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
MAGENTA = '\033[95m'
CYAN = '\033[96m'


class DateBatchTestCase(unittest.TestCase):

    def setUp(self):
        self.table = Table(4,5)
        self.table.cells[0][2] = Cell("Default")
        self.table.cells[1][0] = Cell("Red left", 1, '<', RED)
        self.table.cells[2][1] = Cell("Two\nlines", 0, '<', YELLOW)
        self.table.cells[2][2] = Cell("Three lines of\nquite large\ncentered text.", color=CYAN)
        self.table.cells[2][3] = Cell("One line", 0, '<', YELLOW)
        self.table.cells[4][0] = Cell("2 padded", 2, '^', color=GREEN)
        self.table.cells[4][3] = Cell("Right\naligned", 1, '>', BLUE)
    
    def testColorTable(self):
        """Test a complex table with pretty lines and color"""
        receiver = io.StringIO()
        self.table.print(unicode=True, color=True, file=receiver)
        expected = ("\x1b[90m┌────────────┬─────┬────────────────┬─────────┐\n"
                    "\x1b[90m│\x1b[97m            \x1b[90m│\x1b[97m     \x1b[90m│\x1b[97m    Default     \x1b[90m│\x1b[97m         \x1b[90m│\n"
                    "├────────────┼─────┼────────────────┼─────────┤\n"
                    "\x1b[90m│\x1b[91m Red left   \x1b[90m│\x1b[97m     \x1b[90m│\x1b[97m                \x1b[90m│\x1b[97m         \x1b[90m│\n"
                    "├────────────┼─────┼────────────────┼─────────┤\n"
                    "\x1b[90m│\x1b[97m            \x1b[90m│\x1b[93mTwo  \x1b[90m│\x1b[96m Three lines of \x1b[90m│\x1b[93m         \x1b[90m│\n"
                    "\x1b[90m│\x1b[97m            \x1b[90m│\x1b[93mlines\x1b[90m│\x1b[96m  quite large   \x1b[90m│\x1b[93mOne line \x1b[90m│\n"
                    "\x1b[90m│\x1b[97m            \x1b[90m│\x1b[93m     \x1b[90m│\x1b[96m centered text. \x1b[90m│\x1b[93m         \x1b[90m│\n"
                    "├────────────┼─────┼────────────────┼─────────┤\n"
                    "\x1b[90m│\x1b[97m            \x1b[90m│\x1b[97m     \x1b[90m│\x1b[97m                \x1b[90m│\x1b[97m         \x1b[90m│\n"
                    "├────────────┼─────┼────────────────┼─────────┤\n"
                    "\x1b[90m│\x1b[92m  2 padded  \x1b[90m│\x1b[97m     \x1b[90m│\x1b[97m                \x1b[90m│\x1b[94m   Right \x1b[90m│\n"
                    "\x1b[90m│\x1b[92m            \x1b[90m│\x1b[97m     \x1b[90m│\x1b[97m                \x1b[90m│\x1b[94m aligned \x1b[90m│\n"
                    "└────────────┴─────┴────────────────┴─────────┘\x1b[m\n").split('\n')
        actual = receiver.getvalue().split('\n')
        assert_equal(actual, expected)
        print('\n' + '\n'.join(actual))

    def testBasicTable(self):
        """Test a complex table with ascii compatible lines and no color"""
        receiver = io.StringIO()
        self.table.print(unicode=False, color=False, file=receiver)
        expected = ("+------------+-----+----------------+---------+\n"
                    "|            |     |    Default     |         |\n"
                    "+------------+-----+----------------+---------+\n"
                    "| Red left   |     |                |         |\n"
                    "+------------+-----+----------------+---------+\n"
                    "|            |Two  | Three lines of |         |\n"
                    "|            |lines|  quite large   |One line |\n"
                    "|            |     | centered text. |         |\n"
                    "+------------+-----+----------------+---------+\n"
                    "|            |     |                |         |\n"
                    "+------------+-----+----------------+---------+\n"
                    "|  2 padded  |     |                |   Right |\n"
                    "|            |     |                | aligned |\n"
                    "+------------+-----+----------------+---------+\n").split('\n')
        actual = receiver.getvalue().split('\n')
        assert_equal(actual, expected)
        print('\n' + '\n'.join(actual))
        

if __name__ == "__main__": 
    
    # This way of running allows quick focus on a particular test by entering the number, or all
    # tests by just entering "test" 
    ldr = unittest.TestLoader()
    
    ldr.testMethodPrefix = "test"
    
    suite = ldr.loadTestsFromTestCase(DateBatchTestCase)
    unittest.TextTestRunner(verbosity=2).run(suite)


