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
import sets
import shutil
import readline

from ..database import Database, DatabaseUninitializedError, DatabaseError
from ..documents import Document
from ..source import Sources, SourceError
from ..parser import ParseError
from ..bibtex import Bibtex, BibtexError

############################################################

def set_stdout_codec():
    # set the stdout codec to properly handle utf8 characters
    SYS_STDOUT = sys.stdout
    sys.stdout = codecs.getwriter('utf8')(sys.stdout)

def initdb(xroot, writable=False, create=False, force=False):
    try:
        return Database(xroot, writable=writable, create=create, force=force)
    except DatabaseUninitializedError as e:
        print >>sys.stderr, e.msg
        print >>sys.stderr, "Import a document to initialize."
        sys.exit(1)
    except DatabaseError as e:
        print >>sys.stderr, e.msg
        sys.exit(1)

############################################################

def print_doc_summary(doc):
    docid = doc.get_docid()
    title = doc.get_title()
    if not title:
        title = ''
    tags = doc.get_tags()
    sources = doc.get_sids()
    keys = doc.get_keys()

    print "id:%s [%s] {%s} (%s) \"%s\"" % (
        docid,
        ' '.join(sources),
        ' '.join(keys),
        ' '.join(tags),
        title,
    )

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
        readline.set_completer_delims(' ')
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
        readline.set_completer_delims(' ')
        while True:
            tag = raw_input('tag: ')
            if tag and tag != '':
                tags.append(tag.strip())
            else:
                break
        return tags

    ############################################

    def add(self, query_string, infile=None, sid=None, tags=None, prompt=False):

        doc = None
        bibtex = None

        sources = Sources()
        doc_sid = sid

        if infile:
            infile = os.path.expanduser(infile)

        ##################################
        # open db and get doc

        self.db = initdb(self.xroot, writable=True, create=True)

        # if query provided, find single doc to update
        if query_string:
            if self.db.count(query_string) != 1:
                print >>sys.stderr, "Search '%s' did not match a single document." % query_string
                print >>sys.stderr, "Aborting."
                sys.exit(1)

            for doc in self.db.search(query_string):
                break

        ##################################
        # do fancy option prompting

        if prompt:
            infile = self.prompt_for_file(infile)

        if prompt:
            doc_sids = []
            if doc_sid:
                doc_sids = [doc_sid]
            # scan the file for source info
            if infile:
                print >>sys.stderr, "Scanning document for source identifiers..."
                try:
                    ss = sources.scan_file(infile)
                except ParseError as e:
                    print >>sys.stderr, "\n"
                    print >>sys.stderr, "Parse error: %s" % e
                    sys.exit(1)
                if len(ss) == 0:
                    print >>sys.stderr, "0 source ids found."
                else:
                    if len(ss) == 1:
                        print >>sys.stderr, "1 source id found:"
                    else:
                        print >>sys.stderr, "%d source ids found:" % (len(ss))
                    for sid in ss:
                        print >>sys.stderr, "  %s" % (sid)
                    doc_sids += [s.sid for s in ss]
            doc_sid = self.prompt_for_source(doc_sids)
            tags = self.prompt_for_tags(tags)

        if not query_string and not infile and not doc_sid:
            print >>sys.stderr, "Must specify file or source to import, or query to update existing document."
            sys.exit(1)

        ##################################
        # process source and get bibtex

        # check if source is a file, in which case interpret it as bibtex
        if doc_sid and os.path.exists(doc_sid):
            bibtex = doc_sid

        elif doc_sid:
            # get source object for sid string
            try:
                source = sources.match_source(doc_sid)
            except SourceError as e:
                print >>sys.stderr, e
                sys.exit(1)

            # check that the source doesn't match an existing doc
            sdoc = self.db.doc_for_source(source.sid)
            if sdoc:
                if doc and sdoc != doc:
                    print >>sys.stderr, "A different document already exists for source '%s'." % (sid)
                    print >>sys.stderr, "Aborting."
                    sys.exit(1)
                print >>sys.stderr, "Source '%s' found in database.  Updating existing document..." % (sid)
                doc = sdoc

            try:
                print >>sys.stderr, "Retrieving bibtex...",
                bibtex = source.fetch_bibtex()
                print >>sys.stderr, "done."
            except BibtexError as e:
                print >>sys.stderr, "\n"
                print >>sys.stderr, "Could not retrieve bibtex: %s" % e
                sys.exit(1)

        ##################################

        # if we still don't have a doc, create a new one
        if not doc:
            doc = Document(self.db)

        ##################################
        # add stuff to the doc

        if bibtex:
            try:
                print >>sys.stderr, "Adding bibtex...",
                doc.add_bibtex(bibtex)
                print >>sys.stderr, "done."
            except BibtexError as e:
                print >>sys.stderr, "\n"
                print >>sys.stderr, e
                print >>sys.stderr, "Bibtex must be a plain text file with a single bibtex entry."
                sys.exit(1)
            except:
                print >>sys.stderr, "\n"
                raise

        if infile:
            path = os.path.abspath(infile)
            try:
                print >>sys.stderr, "Adding file '%s'..." % (path),
                doc.add_file(path)
                print >>sys.stderr, "done."
            except ParseError as e:
                print >>sys.stderr, "\n"
                print >>sys.stderr, "Parse error: %s" % e
                sys.exit(1)
            except:
                print >>sys.stderr, "\n"
                raise

        if tags:
            try:
                print >>sys.stderr, "Adding tags...",
                doc.add_tags(tags)
                print >>sys.stderr, "done."
            except:
                print >>sys.stderr, "\n"
                raise

        ##################################
        # sync the doc to db and disk

        try:
            print >>sys.stderr, "Syncing document...",
            doc.sync()
            print >>sys.stderr, "done.\n",
        except:
            print >>sys.stderr, "\n"
            raise

        print_doc_summary(doc)
        return doc.docid

    ############################################

    def importbib(self, bibfile, tags=[], overwrite=False):
        self.db = initdb(self.xroot, writable=True, create=True)

        errors = []

        sources = Sources()

        for entry in sorted(Bibtex(bibfile), key=lambda entry: entry.key):
            print >>sys.stderr, entry.key

            try:
                docs = []

                # check for doc with this bibkey
                bdoc = self.db.doc_for_bib(entry.key)
                if bdoc:
                    docs.append(bdoc)

                # check for known sids
                for source in sources.scan_bibentry(entry):
                    sdoc = self.db.doc_for_source(source.sid)
                    # FIXME: why can't we match docs in list?
                    if sdoc and sdoc.docid not in [doc.docid for doc in docs]:
                        docs.append(sdoc)

                if len(docs) == 0:
                    doc = Document(self.db)
                elif len(docs) > 0:
                    if len(docs) > 1:
                        print >>sys.stderr, "  Multiple distinct docs found for entry.  Using first found."
                    doc = docs[0]
                    print >>sys.stderr, "  Updating id:%s..." % (doc.docid)

                doc.add_bibentry(entry)

                filepath = entry.get_file()
                if filepath:
                    print >>sys.stderr, "  Adding file: %s" % filepath
                    doc.add_file(filepath)

                doc.add_tags(tags)

                doc.sync()

            except BibtexError as e:
                print >>sys.stderr, "  Error processing entry %s: %s" % (entry.key, e)
                print >>sys.stderr
                errors.append(entry.key)

        if errors:
            print >>sys.stderr
            print >>sys.stderr, "Failed to import %d" % (len(errors)),
            if len(errors) == 1:
                print >>sys.stderr, "entry",
            else:
                print >>sys.stderr, "entries",
            print >>sys.stderr, "from bibtex:"
            for error in errors:
                print >>sys.stderr, "  %s" % (error)
            sys.exit(1)
        else:
            sys.exit(0)

    ############################################

    def delete(self, query_string, prompt=True):
        self.db = initdb(self.xroot, writable=True)
        count = self.db.count(query_string)
        if count == 0:
            print >>sys.stderr, "No documents found for query."
            sys.exit(1)
        if prompt:
            resp = raw_input("Type 'yes' to delete %d documents: " % count)
            if resp != 'yes':
                print >>sys.stderr, "Aborting."
                sys.exit(1)
        for doc in self.db.search(query_string):
            doc.purge()

    ############################################

    def update_all(self):
        self.db = initdb(self.xroot, writable=True)
        for doc in self.db.search('*', limit=0):
            try:
                print >>sys.stderr, "Updating %s..." % doc.docid,
                doc.update_from_bibtex()
                doc.sync()
                print >>sys.stderr, "done."
            except:
                print >>sys.stderr, "\n"
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
        if oformat not in ['summary','bibtex','tags','sources','keys','files']:
            print >>sys.stderr, "Unknown output format."
            sys.exit(1)

        set_stdout_codec()

        self.db = initdb(self.xroot)

        if query_string == '*' and oformat in ['tags','sources','keys']:
            if oformat == 'tags':
                for tag in self.db.get_terms('tag'):
                    print tag
            elif oformat == 'sources':
                for source in self.db.get_sids():
                    print source
            elif oformat == 'keys':
                for key in self.db.get_terms('key'):
                    print key
            return

        otags = set([])
        osources = set([])
        okeys = set([])

        for doc in self.db.search(query_string, limit=limit):
            if oformat in ['summary']:
                print_doc_summary(doc)
                continue

            elif oformat in ['file','files']:
                for path in doc.get_fullpaths():
                    print "%s" % (path)
                continue

            elif oformat == 'bibtex':
                bibtex = doc.get_bibtex()
                if not bibtex:
                    print >>sys.stderr, "No bibtex for doc id:%s." % doc.docid
                else:
                    print bibtex
                    print
                continue

            if oformat == 'tags':
                otags = otags | set(doc.get_tags())
            elif oformat == 'sources':
                osources = osources | set(doc.get_sids())
            elif oformat == 'keys':
                okeys = okeys | set(doc.get_keys())

        if oformat == 'tags':
            for tag in otags:
                print tag
        elif oformat == 'sources':
            for source in osources:
                print source
        elif oformat == 'keys':
            for key in okeys:
                print key

    ############################################

    def count(self, query_string):
        set_stdout_codec()

        self.db = initdb(self.xroot)

        count = self.db.count(query_string)
        print count

    ############################################

    def dumpterms(self, query_string):
        set_stdout_codec()

        self.db = initdb(self.xroot)

        for doc in self.db.search(query_string):
            for term in doc.doc:
                print term.term

    ############################################

    def export(self, outdir, query_string):
        set_stdout_codec()

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
