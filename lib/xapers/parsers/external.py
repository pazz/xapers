import re
from xapers.parser import DocParser, ParseError
from helper import call_cmd


class SubprocessDocParser(DocParser):
    def __init__(self, totext_cmd, metadata_cmd=None, metadata_re=None):
        """
        :param totext_cmd: command (list) to extract the text off a document.
        :param metadata_cmd: shell command used to read a documents metadata.
                           
        In both parameters, the string "%{PATH}" will be substituted.
        """
        self.totext_cmd = totext_cmd
        self.metadata_cmd = metadata_cmd
        self.metadata_re = metadata_re

    def extract_text(self, path):
        cmd = map(lambda x: x.format(PATH=path), self.totext_cmd)
        out, err, rval = call_cmd(cmd)
        if rval != 0:
            raise ParseError(err)
        return out

    def extract_metadata(self, path):
        result = {}
        if self.metadata_cmd is not None and self.metadata_re is not None:
            cmd = map(lambda x: x.format(PATH=path), self.metadata_cmd)
            out, err, rval = call_cmd(cmd)
            if rval != 0:
                raise ParseError(err)
            match = re.match(self.metadata_re, out)
            if match:
                result = match.groups()
        return result
