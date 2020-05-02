#========================================================
# tagwriter.py
#========================================================
# PublicPermissions: True
#========================================================

"""Simple class to output XML/HTML style formatted text with elements and attributes."""

class TagWriter(object):
    """Simplistic class to write XML/HTML style tagged text to a file"""

    def __init__(self, filename):
        self.__f = open(filename, 'w')
        self.__stack = []
        self.filename = filename

    def __del__(self):
        self.__f.close()

    def write(self, tag, attributes='', text=''):
        """Writes a tag including attributes, of name tag, and containing text."""
        self.__f.write("<{}".format(tag))
        if attributes != '':
            self.__f.write(" {}".format(attributes))
        self.__f.write(">{}</{}>\n".format(text, tag))

    def write_orphan(self, tag, attributes):
        """Writes an unclosed tag without adding it to the stack."""
        self.__f.write("<{} {}>\n".format(tag, attributes))

    def write_text(self, text):
        """Writes the supplied text directly."""
        self.__f.write(text)

    def open(self, tag, attributes=''):
        """Opens a new nested tag."""
        if attributes == '':
            self.__f.write("<{}>\n".format(tag))
        else:
            self.__f.write("<{} {}>\n".format(tag, attributes))
        self.__stack.append("</{}>\n".format(tag))

    def close(self, count=1):
        """Closes count number of open tags."""
        for _ in range(count): #@UnusedVariable
            self.__f.write(self.__stack.pop())

    def depth(self):
        """Returns the number of currenly open tags."""
        return len(self.__stack)
