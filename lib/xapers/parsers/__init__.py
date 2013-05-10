import os
from ..parser import ParseError
from .pdf import Parser as PDFParser

DOCUMENT_PARSERS = {
    'application/pdf': PDFParser,
}


def parse_file(path):
    # FIXME: determine mime type
    mimetype = 'application/pdf'


    # TODO: use magic (libfile) to extract mimetype, look up corresponding
    # parser in a local dict
    _, fileext = os.path.splitext(path)
    if fileext.lower() == '.pdf':  # prevent this for anything not pdf for now
        parser = DOCUMENT_PARSERS[mimetype]
        try:
            text = parser(path).extract()
            return text
        except Exception, e:
            raise ParseError("Could not parse file: %s" % e)
