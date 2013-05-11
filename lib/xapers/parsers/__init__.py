import os
from ..parser import ParseError
from .pdf import Parser as PDFParser
from .helper import magic_mimetype, magic_encoding

DOCUMENT_PARSERS = {
    'application/pdf': PDFParser(),
}


def parse_file(path):
    text = ''
    try:
        mimetype = magic_mimetype(path)
    except OSError as e:
        raise ParseError('Could not determine mimetype for %s:\n' % (path, e))

    if mimetype == 'application/pdf':  # prevent this for anything not pdf for now
        parser = DOCUMENT_PARSERS[mimetype]
        try:
            text = parser.extract_text(path)  #TODO: give encoding to parser as hint
        except Exception, e:
            raise ParseError("Could not parse file: %s" % e)
    return text
