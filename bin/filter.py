#!/usr/bin/env python

import sys
from ufo_filter import Context, EBContext, Parser

# A trivial but useful implementation of configure
def usage():
    print "usage: filter.py <tagfile> <infile> <outfile>"


argc = len(sys.argv)
if argc < 3:
    print "Not enough arguments"
    usage()
    sys.exit(1)

tagfile = sys.argv[1]
infile = sys.argv[2]
outfile = sys.argv[3]

# Load a context from tagfile
ctx = Context()
ctx.ENABLE_TAG_APPENDS = 1
ctx.loadTagDefs(tagfile)

# Parse the infile for tags!!
Parser(infile, outfile, ctx)

sys.exit(0)