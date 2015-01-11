#=============================================================
# Table.py
#=============================================================
# Jody Sankey
#=============================================================
# PublicPermissions: True
#=============================================================
# Class to build and output a textual table to a stream. Note,
# bad things will happen if the table is not rectangular but
# this condition is not yet enforced.
#=============================================================

import sys 

ASCII_CHR =   (('+','+','+'),('+','+','+'),('+','+','+'),('-','|'))
UNICODE_CHR = (('┌','├','└'),('┬','┼','┴'),('┐','┤','┘'),('─','│'))

GREY = '\033[90m'
WHITE = '\033[97m'
RESET_COLOR = '\033[m'

class Cell:
    """A single cell within a text table."""
    def __init__(self, text, padding=1, alignment='^', color=WHITE):
        """Construct a cell with the specified list of text lines."""
        self.lines = [' ' * padding + t + ' ' * padding for t in text.split('\n')]
        self.alignment = alignment
        self.color = color
    
    def width(self):
        """Returns the maximum width of any line."""
        return max(len(line) for line in self.lines)
        
    def height(self):
        """Returns the number of lines of text."""
        return len(self.lines)
        
    def _pad(self, width, height):
        """Expands the text to the given dimensions."""
        fmt_string = '{{:{}{}}}'.format(self.alignment, width)
        extra_lines = height - len(self.lines)
        self.lines = ([' ' * width] * (extra_lines // 2)
            + [fmt_string.format(line) for line in self.lines]
            + [' ' * width] * (extra_lines - extra_lines // 2))


class Table:
    def __init__(self, width, height):
        """Construct a new table with the specified dimensions."""
        #self.cells = list((list( (Cell('xx') for x in range(width))) for y in range(height)))
        self.cells = [[Cell('') for _ in range(width)] for _ in range(height)]

    def print(self, unicode=True, color=True, file=sys.stdout):
        heights = [max((cell.height() for cell in row)) for row in self.cells]
        widths = [max((cell.width() for cell in column)) for column in zip(*self.cells)]
        for height, row in zip(heights, self.cells):
            for width, cell in zip(widths, row):
                cell._pad(width, height)

        border_col = GREY if color else ''
        chrs = UNICODE_CHR if unicode else ASCII_CHR
        v = border_col + chrs[3][1]
        sep_lines = [chrs[0][p] + chrs[1][p].join((chrs[3][0]*w for w in widths)) +
                    chrs[2][p] for p in range(3)]

        print(border_col + sep_lines[0], file=file)
        for row in self.cells:
            for i in range(row[0].height()):
                l = v + v.join([(cell.color if color else '') + cell.lines[i] for cell in row]) + v
                print(l, file=file)
            if row != self.cells[-1]:
                print(sep_lines[1], file=file)
        print(sep_lines[2] + (RESET_COLOR if color else ''), file=file)


