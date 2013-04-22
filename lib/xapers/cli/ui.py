"""
This file is part of xapers.

Xapers is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or (at your
option) any later version.

Xapers is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
for more details.

You should have received a copy of the GNU General Public License
along with notmuch.  If not, see <http://www.gnu.org/licenses/>.

Copyright 2012, 2013
Jameson Rollins <jrollins@finestructure.net>
"""

import os
import sys
import codecs
SYS_STDOUT = sys.stdout
sys.stdout = codecs.getwriter('utf8')(sys.stdout)
import sets
import shutil
import readline
import logging

from xapers.database import Database, DatabaseError
from xapers.documents import Document
from xapers.bibtex import Bibtex, BibtexError
import xapers.source


############################################################

def initdb(xroot, writable=False, create=False, force=False):
    try:
        return Database(xroot, writable=writable, create=create, force=force)
    except DatabaseError as e:
        logging.error(e.msg)
        logging.error('Import a document to initialize.')
        sys.exit(e.code)

############################################################

class UI():
    """Xapers command-line UI."""

    def __init__(self, xroot):
        self.xroot = xroot
        self.db = None

    ##########

    def prompt_for_file(self, infile):
        if infile:
            print >>sys.stderr, 'file: %s' % infile
        else:
            readline.set_startup_hook()
            readline.parse_and_bind('')
            readline.set_completer()
            infile = raw_input('file: ')
            if infile == '':
                infile = None
        return infile

    def prompt_for_source(self, sources):
        if sources:
            readline.set_startup_hook(lambda: readline.insert_text(sources[0]))
        elif self.db:
            sources = self.db.get_terms('source')
        readline.parse_and_bind("tab: complete")
        completer = Completer(sources)
        readline.set_completer(completer.terms)
        source = raw_input('source: ')
        if source == '':
            source = None
        return source

    def prompt_for_tags(self, tags):
        # always prompt for tags, and append to initial
        if tags:
            print >>sys.stderr, 'initial tags: %s' % ' '.join(tags)
        else:
            tags = []
        if self.db:
            itags = self.db.get_terms('tag')
        else:
            itags = None
        readline.set_startup_hook()
        readline.parse_and_bind("tab: complete")
        completer = Completer(itags)
        readline.set_completer(completer.terms)
        while True:
            tag = raw_input('tag: ')
            if tag and tag != '':
                tags.append(tag.strip())
            else:
                break
        return tags

    ############################################

    def add(self, query_string, infile=None, source=None, tags=None, prompt=False):

        doc = None
        bibtex = None
        smod = None

        ##################################
        # open db and get doc

        self.db = initdb(self.xroot, writable=True, create=True)

        # if query provided, find single doc to update
        if query_string:
            if self.db.count(query_string) != 1:
                logging.error("Search did not match a single document.  Aborting.")
                sys.exit(1)

            for doc in self.db.search(query_string):
                break

        ##################################
        # do fancy option prompting

        if prompt:
            infile = self.prompt_for_file(infile)

        if infile:
            infile = os.path.expanduser(infile)
            if not os.path.exists(infile):
                logging.error("Specified file '%s' not found." % infile)
                sys.exit(1)

        if prompt:
            sources = []
            if source:
                sources = [source]
            # scan the file for source info
            if infile:
                logging.info("Scanning document for source identifiers...")
                ss = xapers.source.scan_for_sources(infile)
                logging.info("%d source ids found:" % (len(sources)))
                if len(sources) > 0:
                    for sid in ss:
                        logging.info("  %s" % sid)
                    sources += ss
            source = self.prompt_for_source(sources)
            tags = self.prompt_for_tags(tags)

        if not query_string and not infile and not source:
            logging.error("Must specify file or source to import, or query to update existing document.")
            sys.exit(1)

        ##################################
        # process source and get bibtex

        # check if source is a file, in which case interpret it as bibtex
        if source and os.path.exists(source):
            bibtex = source

        elif source:
            try:
                smod = xapers.source.get_source(source)
            except xapers.source.SourceError as e:
                logging.exception(e)
                sys.exit(1)

            sid = smod.get_sid()
            if not sid:
                logging.error("Source ID not specified.")
                sys.exit(1)

            # check that the source doesn't match an existing doc
            for tdoc in self.db.search(sid):
                if doc:
                    if tdoc != doc:
                        logging.error("Document already exists for source '%s'. Aborting." % sid)
                        sys.exit(1)
                else:
                    logging.info("Updating existing document...")
                    doc = tdoc
                break

        if smod:
            try:
                logging.info("Retrieving bibtex...")
                bibtex = smod.get_bibtex()
                logging.info("done.")
            except Exception, e:
                logging.error("Could not retrieve bibtex: %s")
                logging.exception(e)
                sys.exit(1)

        ##################################

        # if we still don't have a doc, create a new one
        if not doc:
            doc = Document(self.db)

        ##################################
        # add stuff to the doc

        if bibtex:
            try:
                logging.info("Adding bibtex...")
                doc.add_bibtex(bibtex)
                logging.info("done.")
            except BibtexError, e:
                logging.exception(e)
                logging.error("Bibtex must be a plain text file with a single bibtex entry.")
                sys.exit(1)
            except:
                raise

        if infile:
            path = os.path.abspath(infile)
            try:
                logging.info("Adding file '%s'..." % path)
                # FIXME: check if file already exists?
                # can be done with os.path.isfile
                doc.add_file(path)
                logging.info("done.")
            except:
                raise

        if tags:
            try:
                logging.info("Adding tags...")
                doc.add_tags(tags)
                logging.info("done.")
            except:
                # TODO: if you only raise it anyway just drop the try/except?
                raise

        ##################################
        # sync the doc to db and disk

        try:
            logging.info("Syncing document...")
            doc.sync()
            logging.info("done.")
        except:
            raise

        print "id:%s" % doc.docid
        return doc.docid

    ############################################

    def delete(self, query_string, prompt=True):
        self.db = initdb(self.xroot, writable=True)
        count = self.db.count(query_string)
        if count == 0:
            logging.error("No documents found for query.")
            sys.exit(1)
        if prompt:
            resp = raw_input("Type 'yes' to delete %d documents: " % count)
            if resp != 'yes':
                logging.error("Aborting.")
                sys.exit(1)
        for doc in self.db.search(query_string):
            doc.purge()

    ############################################

    def update_all(self):
        self.db = initdb(self.xroot, writable=True)
        for doc in self.db.search('*', limit=0):
            try:
                logging.info("Updating %s..." % doc.docid)
                doc.update_from_bibtex()
                doc.sync()
                logging.info("done.")
            except:
                raise

    ############################################

    def tag(self, query_string, add_tags, remove_tags):
        self.db = initdb(self.xroot, writable=True)

        for doc in self.db.search(query_string):
            doc.add_tags(add_tags)
            doc.remove_tags(remove_tags)
            doc.sync()

    ############################################

    def search(self, query_string, oformat='summary', limit=None):
        self.db = initdb(self.xroot)

        if oformat == 'tags' and query_string == '*':
            for tag in self.db.get_terms('tag'):
                print tag
            return
        if oformat == 'sources' and query_string == '*':
            for source in self.db.get_sids():
                print source
            return
        if oformat == 'keys' and query_string == '*':
            for key in self.db.get_terms('key'):
                print key
            return

        otags = set([])
        osources = set([])

        for doc in self.db.search(query_string, limit=limit):
            docid = doc.get_docid()

            if oformat in ['file','files']:
                # FIXME: could this be multiple paths?
                for path in doc.get_fullpaths():
                    print "%s" % (path)
                continue

            tags = doc.get_tags()
            sources = doc.get_sids()

            if oformat == 'tags':
                otags = otags | set(tags)
                continue
            if oformat == 'sources':
                osources = osources | set(sources)
                continue

            title = doc.get_title()
            if not title:
                title = ''

            if oformat in ['summary']:
                print "id:%s [%s] (%s) \"%s\"" % (docid,
                                                   ' '.join(sources),
                                                   ' '.join(tags),
                                                   title,
                                                   )
                continue

            if oformat == 'bibtex':
                bibtex = doc.get_bibtex()
                if not bibtex:
                    logging.error("No bibtex for doc id:%s." % docid)
                else:
                    print bibtex
                    print
                continue

        if oformat == 'tags':
            for tag in otags:
                print tag
            return
        if oformat == 'sources':
            for source in osources:
                print source
            return

    ############################################

    def count(self, query_string):
        self.db = initdb(self.xroot)

        count = self.db.count(query_string)
        print count

    ############################################

    def dumpterms(self, query_string):
        self.db = initdb(self.xroot)

        for doc in self.db.search(query_string):
            for term in doc.doc:
                print term.term

    ############################################

    def export(self, outdir, query_string):
        self.db = initdb(self.xroot)

        try:
            os.makedirs(outdir)
        except:
            pass
        for doc in self.db.search(query_string):
            title = doc.get_title()
            origpaths = doc.get_fullpaths()
            nfiles = len(origpaths)
            for path in origpaths:
                if not title:
                    name = os.path.basename(os.path.splitext(path)[0])
                else:
                    name = '%s' % (title.replace(' ','_'))
                ind = 0
                if nfiles > 1:
                    name += '.%s' % ind
                    ind += 1
                name += '.pdf'
                outpath = os.path.join(outdir,name)
                print outpath
                shutil.copyfile(path, outpath.encode('utf-8'))

    ############################################

    def restore(self):
        self.db = initdb(self.xroot, writable=True, create=True, force=True)
        self.db.restore(log=True)

############################################################

# readline completion class
class Completer:
    def __init__(self, words):
        self.words = words
    def terms(self, prefix, index):
        matching_words = [
            w for w in self.words if w.startswith(prefix)
            ]
        try:
            return matching_words[index]
        except IndexError:
            return None
