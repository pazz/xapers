import os
from ..parser import ParseError
from .pdf import Parser as PDFParser
from .helper import magic_mimetype, magic_encoding

DOCUMENT_PARSERS = {
    'application/pdf': PDFParser,
}


def parse_file(path):
    text = ''
    try:
        mimetype = magic_mimetype(path)
    except OSError:
        raise ParseError('Could not determine mimetype for %s' % path)

    if mimetype == 'application/pdf':  # prevent this for anything not pdf for now
        parser = DOCUMENT_PARSERS[mimetype]
        try:
            text = parser(path).extract()  #TODO: give encoding to parser as hint
        except Exception, e:
            raise ParseError("Could not parse file: %s" % e)
    return text
