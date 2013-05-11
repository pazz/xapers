from ..parser import ParseError
from .external import SubprocessDocParser
from .helper import magic_mimetype, magic_encoding

DOCUMENT_PARSERS = {
    'application/pdf': SubprocessDocParser(['pdftotext', '{PATH}', '-']),
    'application/postscript': SubprocessDocParser(['ps2txt', '{PATH}']),
}


def parse_file(path):
    text = ''
    try:
        mimetype = magic_mimetype(path)
    except OSError as e:
        raise ParseError('Could not determine mimetype for %s:\n' % (path, e))

    if mimetype in DOCUMENT_PARSERS:
        parser = DOCUMENT_PARSERS[mimetype]
        try:
            text = parser.extract_text(path)  #TODO: give encoding to parser as hint
        except Exception, e:
            raise ParseError("Could not parse file: %s" % e)
    return text
