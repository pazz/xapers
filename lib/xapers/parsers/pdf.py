from ..parser import ParserBase, ParseError
from helper import call_cmd


class Parser(ParserBase):
    def extract(self):
        out, err, rval = call_cmd(['pdftotext', self.path, '-'])

        if rval != 0:
            msg = 'pdftotext returned with exit code %d.\n%s' % (rval, err)
            raise ParseError(msg)

        return out
