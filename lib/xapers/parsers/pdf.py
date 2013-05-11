from ..parser import DocParser,ParserBase, ParseError
from helper import call_cmd


class Parser(DocParser):
    def extract_text(self, path):
        out, err, rval = call_cmd(['pdftotext', path, '-'])

        if rval != 0:
            msg = 'pdftotext returned with exit code %d.\n%s' % (rval, err)
            raise ParseError(msg)

        return out
