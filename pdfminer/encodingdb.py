#!/usr/bin/env python
import re
from .psparser import PSLiteral
from .glyphlist import glyphname2unicode
from .latin_enc import ENCODING


STRIP_NAME = re.compile(r'[0-9]+')


# windings ...
glyphname2unicode_ext = {
    'oneinv': u'\u278A',
    'twoinv': u'\u278B',
    'threeinv': u'\u278C',
    'fourinv': u'\u278D',
    'fiveinv': u'\u278E',
    'sixinv': u'\u278F',
    'seveninv': u'\u2790',
    'eightinv': u'\u2791',
    'nineinv': u'\u2792',
    'teninv': u'\u2793',

    'onesansinv': u'\u278A',
    'twosansinv': u'\u278B',
    'threesansinv': u'\u278C',
    'foursansinv': u'\u278D',
    'fivesansinv': u'\u278E',
    'sixsansinv': u'\u278F',
    'sevensansinv': u'\u2790',
    'eightsansinv': u'\u2791',
    'ninesansinv': u'\u2792',
    'tensansinv': u'\u2793',

    'handbckptright': u'\u261E',
    'xrhombus': u'\u2756',
    'boxcheckbld': u'\u2611',
}

##  name2unicode
##
def name2unicode(name):
    """Converts Adobe glyph names to Unicode numbers."""
    if name in glyphname2unicode:
        return glyphname2unicode[name]
    if name in glyphname2unicode_ext:
        return glyphname2unicode_ext[name]
    m = STRIP_NAME.search(name)
    if not m:
        raise KeyError(name)
    return unichr(int(m.group(0)))


##  EncodingDB
##
class EncodingDB(object):

    std2unicode = {}
    mac2unicode = {}
    win2unicode = {}
    pdf2unicode = {}
    for (name, std, mac, win, pdf) in ENCODING:
        c = name2unicode(name)
        if std:
            std2unicode[std] = c
        if mac:
            mac2unicode[mac] = c
        if win:
            win2unicode[win] = c
        if pdf:
            pdf2unicode[pdf] = c

    encodings = {
        'StandardEncoding': std2unicode,
        'MacRomanEncoding': mac2unicode,
        'WinAnsiEncoding': win2unicode,
        'PDFDocEncoding': pdf2unicode,
    }

    @classmethod
    def get_encoding(klass, name, diff=None):
        cid2unicode = klass.encodings.get(name, klass.std2unicode)
        if diff:
            cid2unicode = cid2unicode.copy()
            cid = 0
            for x in diff:
                if isinstance(x, int):
                    cid = x
                elif isinstance(x, PSLiteral):
                    try:
                        cid2unicode[cid] = name2unicode(x.name)
                    except KeyError:
                        pass
                    cid += 1
        return cid2unicode
