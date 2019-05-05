#!/usr/bin/env python
from .psparser import LIT


##  PDFColorSpace
##
LITERAL_DEVICE_GRAY = LIT('DeviceGray')
LITERAL_DEVICE_RGB = LIT('DeviceRGB')
LITERAL_DEVICE_CMYK = LIT('DeviceCMYK')


class PDFColorSpace(object):

    def __init__(self, name, ncomponents):
        self.name = name
        self.ncomponents = ncomponents
        return

    def __repr__(self):
        return '<PDFColorSpace: %s, ncomponents=%d>' % (self.name, self.ncomponents)


PREDEFINED_COLORSPACE = dict(
    (name, PDFColorSpace(name, n)) for (name, n) in {
        'CalRGB': 3,
        'CalGray': 1,
        'Lab': 3,
        'DeviceRGB': 3,
        'DeviceCMYK': 4,
        'DeviceGray': 1,
        'Separation': 1,
        'Indexed': 1,
        'Pattern': 1,
    }.iteritems())


##  PDFColor
##
class PDFColor(object):

    def __init__(self, cs=None, clr=None):
        self.cs = cs
        self.clr = clr
        return

    def set(self, cs, clr):
        self.cs = cs
        self.clr = clr

    # color-space
    def set_cs(self, cs):
        self.cs = cs
        return

    # set stroke color-space
    def set_clr(self, clr):
        self.clr = clr
        return

    def copy(self):
        return PDFColor(self.cs, self.clr)

    def __repr__(self):
        return '<%s>:%r' % (self.cs.name, self.clr)

