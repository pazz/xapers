import os

##################################################

class ParseError(Exception):
    """Base class for Xapers parser exceptions."""
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg

##################################################

class ParserBase():
    """Base class for Xapers document parsering."""
    def __init__(self, path):
        self.path = os.path.expanduser(path)

    def extract(self):
        pass
