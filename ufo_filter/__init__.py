import sys
import re
import os
import os.path
import string

####################################################################
# Filter.py
#
# Author: Russell Balest
# E-mail: russell@balest.com
#
# Copyright (C) 2002 Russell Balest
# Copyright (C) 2003 Russell Balest
# Copyright (C) 2004 Russell Balest
# Copyright (C) 2005 Russell Balest
# Copyright (C) 2006 Russell Balest
#
# History:
#
# * Mar 2006 Extended function tag syntax to support argument passing.
# * Feb 2002 Ported to Python from original 1997 Tcl/Tk version.
#
# The Filter module is useful for replacing 'tags' in a template with
# substition text and outputting to a second file.  The tags
# must be of the form @TAGNAME@.  To safely escape the literal
# @ symbol, use the construction @@@.  The replacement algorithm
# is super-recursive, so the substitution text can include more tags.
# Tags are defined within a Context in one of 3 ways.  Tags can be read
# from a tag definition file.  The format of this file is simply a tag
# in the first column and everything else on the line is the
# replacement text. See the tag definition regex below.  Tags can be
# defined statically within a program using the Context method tagDefine().
# See the example below.  Lastly, complex tags can be defined as methods
# within the Context by subclassing the Context class and adding methods.
# This way arbitrary replacement text can be constructed programatically.
# Method tags (method with the same name as the tag) are searched first
# and then static tags are searched if no method tag exists.
#
# Method tags can be called with arguments if the corresponding method
# accepts or requires arguments.  For example:  @FOO(hello)@

# The basic usage of this module is:
#
##################################################################
# import Filter
#
# ctx = Filter.Context()
# ctx.loadTagDefs('mytagdefs.txt')
# ctx.tagDefine('TAG3', 'tag3')
# Filter.Parser('myfile.txt.T', 'myfile.txt', ctx)
#
##################################################################

# The advanced usage of this module is to subclass the Context
# class and supply replacement functions:
#
##################################################################
# import Filter
#
# class MyContext( Filter.Context ):
#    def mytag(self):
#	 return "dynamic replacement text"
#    def mytagwithargs(self, args ...):
#        return "more dynamic replacment text"
#
# ctx = MyContext()
# Filter.Parser('myfile.txt.T', 'myfile.txt', ctx)
#
##################################################################


# The tag RE syntax is:
rex = re.compile(
    '(^|[^@]|@@@|@@@@@@)@((([_\.a-zA-Z0-9]+)\.)?([_a-zA-Z]+[_0-9a-zA-Z \-]*)(\(([_\.0-9/=$@<>()a-zA-Z \-,]*)\))?)@')

# The @ symbol RE is:
atx = re.compile('@@@')

# The native ufo tag definition RE syntax is:
tdrex = re.compile('^(([_\.a-zA-Z0-9]*)\.)?([_a-zA-Z]+[()_0-9a-zA-Z \-]*)[\t]+(.*)$')

# The EB env file RE syntax is:
ebrex = re.compile('^export (([_\.a-zA-Z0-9]*)\.)?([_a-zA-Z]+[()_0-9a-zA-Z \-]*)=[\'\"](.*)[\'\"]$')

# The yaml RE syntax is:
# The EB env file RE syntax is:
yamlrex = re.compile('^(([_\.a-zA-Z0-9]*)\.)?([_a-zA-Z]+[()_0-9a-zA-Z \-]*)=[\'\"]?([^\'^\".]*)[\'\"]?$')

# List of known tag file formats
tdrexes = { 'nv_tab' : tdrex, 'eb_env' : ebrex, 'nv_yaml' : yamlrex }

# To handle recursion level during exceptions
# for more meaningful stack trace.
global alreadyCaught
alreadyCaught = False

# Handlers
global preFilterHandler
global postFilterHandler

preFilterHandler = None
postFilterHandler = None


class InvalidReplacement(Exception):
    def __init__(self, msg=None):
        Exception.__init__(self, msg)


class UnknownContext(Exception):
    def __init__(self, msg=None):
        Exception.__init__(self, msg)


def Parser(infile, outfile, context):
    """
    Parse infile for valid tags and replace them with
    the appropriate substitution text known to context.
    Write the transformed text to outfile.
    """
    newtext = Parse(infile, context)

    if outfile != None:
        ouf = open(outfile, 'w')
        ouf.write("%s" % newtext)
        ouf.close()

    return newtext


def Parse(infile, context):
    """
    Parse infile for valid tags and replace them with
    the appropriate substitution text known to context.
    Return the transformed text as a string.
    """
    # Set the directory of the current file being processed
    # in the context.
    dirname = os.path.dirname(infile)
    context.pushdir(dirname)

    inf = open(infile, 'r')
    linecount = 0
    newtext = ""

    for line in inf.readlines():
        try:
            newline = lineParser(line, context)
            newtext = newtext + newline
            linecount = linecount + 1
        except ValueError, (tag, tline):
            print "  while parsing file: ", infile,
            print "  at line: %d\n" % (linecount)
            raise
    inf.close()
    context.popdir()
    return newtext


def lineParser(line, context, lineByLine=True):
    """
    Parse a single line for filter tags.
    Do multi-pass in case multiple tags exist on a line,
    or a replacement contains a tag.
    Return the modified line.
    """
    global alreadyCaught
    global preFilterHandler
    global postFilterHandler

    linestack = []
    done = False

    while not done:
        linestack.append(line)
        reo = rex.search(line)
        if reo:
            gotns = reo.group(4)
            gottag = reo.group(5)
            gotargv = reo.group(7)

            # In case the argument list contains tags as in:  @foo(@arg@)@
            # Process the argument list before calling the replacement function.
            if gotargv:
                gotargv = lineParser(gotargv, context)

            # If we got a scoped tag, lookup the correct context first.
            if gotns:
                if (context.name == 'gotns'):
                    curctx = context
                else:
                    tmpctx = context.getContext(gotns)
                    if tmpctx:
                        curctx = tmpctx
                    else:
                        print "No such context [ %s ]" % gotns
                        gottag = "UNDEFINED"
                        curctx = context
            else:
                curctx = context

            try:
                newtext = curctx.replace(gottag, gotargv)
                # Only replace 1 occurrence at a time.
                # This is potentially fragile because it allows
                # the possibility that the wrong tag is replaced
                # if there are multiple matches on a line. I'm
                # assuming their is a well defined order on the
                # matches.
                start = reo.start(2) - 1
                line = line[:start] + rex.sub(newtext, line[start:], 1)
            except ValueError, (tag):
                if alreadyCaught:
                    print "  from text: %s" % linestack.pop()
                else:
                    print "  in text: %s" % linestack.pop()
                    alreadyCaught = True
                linestack.reverse()
                remaining = len(linestack)
                for l in linestack:
                    remaining = remaining - 1
                    if not remaining:
                        print "  from original text: %s" % (l)
                    else:
                        print "  from previous text: %s" % (l)
                raise ValueError, (tag, line)
            except InvalidReplacement, e:
                print " Invalid replacement text: ", e
                raise Exception("\n\n###################################################################################################\nCaught exception while parsing @%s@ in line:\n%s\n##################################################################################################\n\n" % (
                    gottag, line[:80]))
            except UnknownContext, e:
                print e
                raise Exception("\n\n###################################################################################################\nGenerated UnknownContext Exception [ %s ] while parsing @%s@ in line:\n##################################################################################################\n\n" % (
                    e, gottag))
            except Exception, e:
                print e
                raise Exception("\n\n###################################################################################################\nCaught exception while parsing @%s@ in line:\n%s\n##################################################################################################\n\n" % (
                    gottag, line[:80]))
        else:
            done = True

    # Finally replace @@@ with @.
    reo = atx.search(line)
    if reo:
        line = atx.sub('@', line)

    if postFilterHandler != None:
        postHandler(line)

    return line

class Context(object):
    def __init__(self, name='.', parent=None):
        self.ALLOW_UNKNOWN_TAGS = 0
        self.ALLOW_DEFAULT_TAGS = True
        self.ALLOW_TAG_OVERRIDES = 0
        self.ENABLE_TAG_APPENDS = 0
        self.ALLOW_TAG_DEFAULTS = True
        self.AUTO_SELECT_TD = True

        self.name = name
        self.tagNames = []
        self.tagDefaults = {}

        self.dirname = ['.']
        if not parent:
            self.parent = self
            self.tdrex = tdrex
        else:
            self.parent = parent
            self.tdrex = parent.tdrex
        self.subcontexts = {}

    def curdir(self):
        return self.dirname[len(self.dirname) - 1]

    def pushdir(self, dirname):
        self.dirname.append(dirname)

    def popdir(self):
        return self.dirname.pop()

    def getParent(self):
        """
        Return the parent context.
        """
        return self.parent

    def getContext(self, name):
        """
        Return the subcontext with the given name.
        """
        if self.subcontexts.has_key(name):
            return self.subcontexts[name]
        else:
            return None
            # raise UnknownContext( name );

    def addContext(self, context):
        """
        Add a context inside this one.
        """
        # print "adding context %s" % context.name
        self.subcontexts[context.name] = context

    def isDefined(self, tag):
        """
        Check if the tag is defined on this Context.
        """
        if hasattr(self, tag):
            return True
        else:
            return False

    def replace(self, gottag, argsv=None):
        """
        Return the replacement text for the given tag.
        """
        # print "GOTTAG: %s" % gottag
        if hasattr(self, gottag):
            attr = getattr(self, gottag)
            if callable(attr):

                if argsv:
                    # Parse the string
                    # remove spaces
                    argsv = string.replace(argsv, ' ', '')
                    argv = string.split(argsv, ',')
                    newtext = attr(*argv)
                else:
                    try:
                        newtext = attr()
                    except Exception as e:
                        print "\n\n##########################\n Caught an exception generated inside the replacement function for tag %s\n##############################\n\n" % (gottag), e
                        raise

            else:
                newtext = attr
        else:
            if False:
                None

            if self.ALLOW_DEFAULT_TAGS:
                newtext = self.getDefault(gottag)
                if newtext:
                    return newtext

            if self.ALLOW_UNKNOWN_TAGS:
                newtext = "%s" % gottag
                print "######## Warning: Undefined tag: '%s'\n" % (gottag)
            else:
                print "\nUndefined tag: '%s'" % (gottag)
                raise ValueError(gottag)

        # if newtext == None:
        #	raise InvalidReplacement(newtext)

        return newtext

    def tagDefault(self, tag, replacement):
        self.tagDefaults[tag] = replacement

    def getDefault(self, tag):
        if self.tagDefaults.has_key(tag):
            return self.tagDefaults[tag]
        else:
            return None

    def tagDefine(self, tag, replacement):
        if hasattr(self, tag):
            if self.ALLOW_TAG_OVERRIDES:
                print "warning: overriding tag definition: %s with: '%s'" % (tag, replacement)
            else:
                if self.ENABLE_TAG_APPENDS:
                    print "warning: appending to tag %s with: '%s'" % (tag, replacement)
                    replacement = getattr(self, tag) + ", " + replacement
                else:
                    print "error: overriding tag definition: %s with: '%s'" % (tag, replacement)
                    raise Exception
        setattr(self, tag, replacement)
        # TODO: Make this uncallable if it's callable.
        # TODO: Make it unique ?
        self.tagNames.append(tag)

    # Try to parse with all known regexes
    # and set the regex accordingly
    def autoSelectTD(self,infile):
        auto_rex=None
        for rex_name in tdrexes.keys():
            rex = tdrexes[rex_name]
            inf = open(infile, 'r')
            for line in inf.readlines():
                try:
                    # Skip comments and blank lines
                    if line[0] != '#' and line[0] != '\n':
                        reo = rex.match(line)
                        if reo:
                            print "Parsing tag definitions as %s" % (rex_name)
                            self.tdrex = rex
                            break
                except:
                    continue
            if auto_rex:
                self.tdrex = auto_rex
                inf.close()
                break

    def loadTagDefs(self, infile):

        if self.AUTO_SELECT_TD:
            self.autoSelectTD(infile)

        inf = open(infile, 'r')
        linecount = 0

        for line in inf.readlines():
            try:
                # Skip comments and blank lines
                if line[0] != '#' and line[0] != '\n':
                    reo = self.tdrex.match(line)
                    if reo:
                        ns = reo.group(2)
                        tag = reo.group(3)
                        val = reo.group(4)
                        if ns:
                            # print "Got namespaced tag: %s" % ns
                            ctx = self.getContext(ns)
                            if not ctx:
                                # add it
                                # print "Adding new Context: %s"  % ns
                                ctx = Context(ns, self)
                                self.addContext(ctx)
                        else:
                            ctx = self
                        # print "defining %s as %s" % (tag,val)
                        # trim whitespace off the value
                        val = string.strip(val, ' \t')
                        ctx.tagDefine(tag, val)
                    else:
                        print "Invalid tag definition: %s" % line
                linecount = linecount + 1
            except ValueError, tag:
                print "Badly formed line: '%s' on line %d" % (line, linecount)

    def list(self):
        for name in self.tagNames:
            value = getattr(self,name)
            print "%s : %s" % (name,value)

    def loadKeyedTagDefs(self, infile, tag):
        """
        Keyed tag definition files correspond to a SINGLE
        TAG which is parameterized by some key which locates
        a context.  The format is: key is the first word ending
        in white space, the value is the remainder of the line.
        """
        inf = open(infile, 'r')
        linecount = 0

        for line in inf.readlines():
            try:
                if line[0] != '#' and line[0] != '\n':
                    reo = tdrex.match(line)
                    if reo:
                        ns = reo.group(1)
                        key = reo.group(2)
                        val = reo.group(3)
                        ctx = self.getContext(key)
                        if ctx:
                            ctx.tagDefine(tag, val)
                        else:
                            print "No such context %s within %s" % (key, self.name)
                    else:
                        print "Invalid tag definition: %s" % line
                linecount = linecount + 1
            except ValueError, tag:
                print "Badly formed line: '%s' on line %d" % (line, linecount)

class EBContext(Context):
    def __init__(self, name='.', parent=None):
        super(EBContext, self).__init__(name, parent)
        # Override the regex for tag definitions with the env based file in EB
        self.tdrex = ebrex

def loadList(infile):
    """
    Load a single column of words from a text file
    and return a list.
    """
    list = []
    inf = open(infile, 'r')
    linecount = 0

    for line in inf.readlines():
        if line[0] != '#' and line[0] != '\n':
            reo = tdrex.match(line)
            ns = reo.group(1)
            key = reo.group(2)
            if list.count(key):
                print "[%s]: %s already in list, ignoring." % (infile, key)
            else:
                list.append(key)
    return list
