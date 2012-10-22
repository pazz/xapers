import sys
import pycurl
import cStringIO
import xapers.bibtex as bibparse

def dccRetrieve(url):
    curl = pycurl.Curl()
    curl.setopt(pycurl.URL, url)
    # --negotiate --cookie foo --cookie-jar foo --user : --location-trusted --insecure
    curl.setopt(pycurl.HTTPAUTH, pycurl.HTTPAUTH_GSSNEGOTIATE)
    #curl.setopt(pycurl.COOKIEFILE, 'foo')
    #curl.setopt(pycurl.COOKIEJAR, 'foo')
    curl.setopt(pycurl.USERPWD, ':')
    curl.setopt(pycurl.FOLLOWLOCATION, 1)
    curl.setopt(pycurl.UNRESTRICTED_AUTH, 1)
    doc = cStringIO.StringIO()
    curl.setopt(pycurl.WRITEFUNCTION, doc.write)
    try:
        curl.perform()
    except:
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
    # FIXME: check return code
    curl.close()
    return doc.getvalue()

def dccXMLExtract(xmlstring):
    from xml.dom.minidom import parse, parseString
    xml = parseString(xmlstring)
    etitle = xml.getElementsByTagName("title")[0].firstChild
    if etitle:
        title = etitle.data
    else:
        title = None
    alist = xml.getElementsByTagName("author")
    authors = []
    for author in alist:
        authors.append(author.getElementsByTagName("fullname")[0].firstChild.data)
    eabstract = xml.getElementsByTagName("abstract")[0].firstChild
    if eabstract:
        abstract = eabstract.data
    else:
        abstract = None
    # FIXME: find year
    year = None
    return title, authors, year, abstract

class Source():
    source = 'dcc'
    netloc = 'dcc.ligo.org'

    def __init__(self, sid=None):
        self.sid = sid

    def gen_url(self):
        return 'http://%s/cgi-bin/private/DocDB/ShowDocument?docid=%s' % (self.netloc, self.sid)

    def parse_url(self, parsedurl):
        loc = parsedurl.netloc
        path = parsedurl.path
        if loc.find(self.netloc) >= 0:
            for query in parsedurl.query.split('&'):
                if 'docid=' in query:
                    field, self.sid = query.split('=')
                    break

    def get_data(self):
        # url = 'http://%s/cgi-bin/private/DocDB/RetrieveFile?docid=' % (self.netloc, self.sid)
        # pdf = dccRetrieve(url)

        if 'file' in dir(self):
            f = open(self.file, 'r')
            xml = f.read()
            f.close()
        else:
            url = self.gen_url() + '&outformat=xml'
            xml = dccRetrieve(url)

        try:
            title, authors, year, abstract = dccXMLExtract(xml)
        except:
            print >>sys.stderr, xml
            raise

        data = {
            'dcc':      self.sid,
            'url':      self.gen_url()
            }

        if title:
            data['title'] = title
        if authors:
            data['authors'] = authors
        if abstract:
            data['abstract'] = abstract
        if year:
            data['year'] = year

        # FIXME: use these fields:
        #   @techreport
        #   institution: LIGO Labratory
        #   number: DCC number
        #   month:

        return data

    def get_bibtex(self):
        data = self.get_data()
        if not data:
            return
        key = '%s:%s' % (self.source, self.sid)
        bibentry = bibparse.data2bib(data, key)
        return bibentry.as_string()
