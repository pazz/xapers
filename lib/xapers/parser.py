import os

##################################################

class ParseError(Exception):
    """Base class for Xapers parser exceptions."""
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg

##################################################

class DocParser(object):
    """Base class for Xapers document parsers"""

    def extract_text(self, path):
        """returns a plaintext version of the document at given path"""
        pass

    def extract_metadata(self, path):
        """returns a dict of metadata for doc at given path"""
        pass
