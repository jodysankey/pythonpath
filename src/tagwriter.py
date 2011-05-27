#========================================================
# tagwriter.py
#========================================================
# $HeadURL:                                             $
# Last $Author: jody $
# $Revision: 742 $
# $Date: 2009-12-28 02:23:37 -0600 (Mon, 28 Dec 2009) $
#========================================================
# Simple class to output XML/HTML style formatted
# text with elements and attributes 
#========================================================


class TagWriter(object):
    """Simplistic class to write XML/HTML style tagged text to a file"""

    def __init__(self,filename):
        self.__f = open(filename,'w')
        self.__stack = []
    def __self__(self):
        self.__f.close()
        
    def write(self,tag,attributes='',text=''): 
        if attributes=='':
            self.__f.write("<{}>{}</{}>\n".format(tag,text,tag))
        else:
            self.__f.write("<{} {}>{}</{}>\n".format(tag,attributes,text,tag))
    def writeText(self,text): 
        self.__f.write(text)
    def open(self,tag,attributes=''):
        if attributes=='':
            self.__f.write("<{}>\n".format(tag))
        else:
            self.__f.write("<{} {}>\n".format(tag,attributes))
        self.__stack.append("</{}>\n".format(tag))
    def close(self): 
        self.__f.write(self.__stack.pop())


