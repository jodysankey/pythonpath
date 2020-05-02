#========================================================
# tagwriter.py
#========================================================
# PublicPermissions: True
#========================================================

"""Simple class to output XML/HTML style formatted text with elements and attributes."""

class TagWriter(object):
    """Simplistic class to write XML/HTML style tagged text to a file"""

    def __init__(self, filename):
        self._f = open(filename, 'w')
        self._stack = []
        self.filename = filename

    def __del__(self):
        self._f.close()

    def write(self, tag, attributes='', text=''):
        """Writes a tag including attributes, of name tag, and containing text."""
        self._f.write("<{}".format(tag))
        if attributes != '':
            self._f.write(" {}".format(attributes))
        self._f.write(">{}</{}>\n".format(text, tag))

    def write_orphan(self, tag, attributes):
        """Writes an unclosed tag without adding it to the stack."""
        self._f.write("<{} {}>\n".format(tag, attributes))

    def write_text(self, text):
        """Writes the supplied text directly."""
        self._f.write(text)

    def open(self, tag, attributes=''):
        """Opens a new nested tag."""
        if attributes == '':
            self._f.write("<{}>\n".format(tag))
        else:
            self._f.write("<{} {}>\n".format(tag, attributes))
        self._stack.append("</{}>\n".format(tag))

    def close(self, count=1):
        """Closes count number of open tags."""
        for _ in range(count): #@UnusedVariable
            self._f.write(self._stack.pop())

    def depth(self):
        """Returns the number of currenly open tags."""
        return len(self._stack)
