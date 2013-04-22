#!/usr/bin/env python

import argparse
import os
import xapers
import logging

# create argument parser
desc = 'import bibtex database into xapers.'
parser = argparse.ArgumentParser(description=desc)
# add mandatory argument for input
parser.add_argument('bib', help='bib-file to import')

#make index rootdor configurable 
xroot = os.getenv('XAPERS_ROOT',
                  os.path.join('~','.xapers','docs'))
parser.add_argument('--xroot', help='path to xapers root', default=xroot)
parser.add_argument('--tags', nargs='*', metavar='tag', default=['new'],
                    help='tags to add to new entries')

# verbosity level
parser.add_argument('-v', '--verbose', action='count', default=0)

#parse arguments
args = parser.parse_args()

dbpath = os.path.expanduser(args.xroot)
bibpath = os.path.expanduser(args.bib)

# set up the verbosity level of the logging system
loglevel = {
    0: logging.WARNING,
    1: logging.INFO,
    2: logging.DEBUG,
}[min(2, args.verbose)]
logging.basicConfig(level = loglevel,
                    format='%(levelname)s: %(message)s')

logging.debug('got arguments: %s' % args)
logging.debug('xroot: %s' % dbpath)
logging.debug('bibfile: %s' % bibpath)

#create xapers db object
db = xapers.Database(dbpath)

# parse bibtex
bib = xapers.bibtex.Bibtex(bibpath)

# Go import
for entry in bib:
    logging.info('adding: %s' % entry.key)
    # TODO: get new document
    #doc = Document(self.db)
    # add tags
    #doc.add_tags(tags)
