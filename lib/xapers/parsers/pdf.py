from StringIO import StringIO
from pdfminer.pdfinterp import PDFResourceManager, process_pdf
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams


def pdf2txt(fp, password='', outcodec='utf-8', caching=True):
    """
    this does what's on the tin.
    possibly raises `pdfminer.pdfinterp.PDFTextExtractionNotAllowed`
    """
    # no idea what this does
    laparams = LAParams()
    rsrcmgr = PDFResourceManager(caching=caching)

    outfp = StringIO()
    device = TextConverter(rsrcmgr, outfp, codec=outcodec, laparams=laparams)
    process_pdf(rsrcmgr, device, fp, set(), maxpages=0, password=password,
                caching=caching, check_extractable=True)
    device.close()
    txt = outfp.getvalue()
    outfp.close()
    return txt


def parse_file(path):
    return pdf2txt(open(path))
