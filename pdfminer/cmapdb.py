#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Adobe character mapping (CMap) support.

CMaps provide the mapping between character codes and Unicode
code-points to character ids (CIDs).

More information is available on the Adobe website:

  http://opensource.adobe.com/wiki/display/cmap/CMap+Resources

"""

import sys
import os
import os.path
import gzip
try:
    import cPickle as pickle
except ImportError:
    import pickle as pickle
import struct
import logging
from .psparser import PSStackParser
from .psparser import PSSyntaxError
from .psparser import PSEOF
from .psparser import PSLiteral
from .psparser import literal_name
from .psparser import KWD
from .encodingdb import name2unicode
from .utils import choplist
from .utils import nunpack


logger = logging.getLogger("pdfminer.cmapdb")


unicode_charset_map = [
    (0x0000, 0x007F, u"C0控制符及基本拉丁文 (C0 Control and Basic Latin)"),
    (0x0080, 0x00FF, u"C1控制符及拉丁文补充, 0x1 (C1 Control and Latin 1 Supplement)"),
    (0x0100, 0x017F, u"拉丁文扩展, 0xA (Latin Extended, 0xA)"),
    (0x0180, 0x024F, u"拉丁文扩展, 0xB (Latin Extended, 0xB)"),
    (0x0250, 0x02AF, u"国际音标扩展 (IPA Extensions)"),
    (0x02B0, 0x02FF, u"空白修饰字母 (Spacing Modifiers)"),
    (0x0300, 0x036F, u"结合用读音符号 (Combining Diacritics Marks)"),
    (0x0370, 0x03FF, u"希腊文及科普特文 (Greek and Coptic)"),
    (0x0400, 0x04FF, u"西里尔字母 (Cyrillic)"),
    (0x0500, 0x052F, u"西里尔字母补充 (Cyrillic Supplement)"),
    (0x0530, 0x058F, u"亚美尼亚语 (Armenian)"),
    (0x0590, 0x05FF, u"希伯来文 (Hebrew)"),
    (0x0600, 0x06FF, u"阿拉伯文 (Arabic)"),
    (0x0700, 0x074F, u"叙利亚文 (Syriac)"),
    (0x0750, 0x077F, u"阿拉伯文补充 (Arabic Supplement)"),
    (0x0780, 0x07BF, u"马尔代夫语 (Thaana)"),
    (0x07C0, 0x077F, u"西非書面語言 (N'Ko)"),
    (0x0800, 0x085F, u"阿维斯塔语及巴列维语 (Avestan and Pahlavi)"),
    (0x0860, 0x087F, u"Mandaic"),
    (0x0880, 0x08AF, u"撒马利亚语 (Samaritan)"),
    (0x0900, 0x097F, u"天城文书 (Devanagari)"),
    (0x0980, 0x09FF, u"孟加拉语 (Bengali)"),
    (0x0A00, 0x0A7F, u"锡克教文 (Gurmukhi)"),
    (0x0A80, 0x0AFF, u"古吉拉特文 (Gujarati)"),
    (0x0B00, 0x0B7F, u"奥里亚文 (Oriya)"),
    (0x0B80, 0x0BFF, u"泰米尔文 (Tamil)"),
    (0x0C00, 0x0C7F, u"泰卢固文 (Telugu)"),
    (0x0C80, 0x0CFF, u"卡纳达文 (Kannada)"),
    (0x0D00, 0x0D7F, u"德拉维族语 (Malayalam)"),
    (0x0D80, 0x0DFF, u"僧伽罗语 (Sinhala)"),
    (0x0E00, 0x0E7F, u"泰文 (Thai)"),
    (0x0E80, 0x0EFF, u"老挝文 (Lao)"),
    (0x0F00, 0x0FFF, u"藏文 (Tibetan)"),
    (0x1000, 0x109F, u"缅甸语 (Myanmar)"),
    (0x10A0, 0x10FF, u"格鲁吉亚语 (Georgian)"),
    (0x1100, 0x11FF, u"朝鲜文 (Hangul Jamo)"),
    (0x1200, 0x137F, u"埃塞俄比亚语 (Ethiopic)"),
    (0x1380, 0x139F, u"埃塞俄比亚语补充 (Ethiopic Supplement)"),
    (0x13A0, 0x13FF, u"切罗基语 (Cherokee)"),
    (0x1400, 0x167F, u"统一加拿大土著语音节 (Unified Canadian Aboriginal Syllabics)"),
    (0x1680, 0x169F, u"欧甘字母 (Ogham)"),
    (0x16A0, 0x16FF, u"如尼文 (Runic)"),
    (0x1700, 0x171F, u"塔加拉语 (Tagalog)"),
    (0x1720, 0x173F, u"Hanunóo"),
    (0x1740, 0x175F, u"Buhid"),
    (0x1760, 0x177F, u"Tagbanwa"),
    (0x1780, 0x17FF, u"高棉语 (Khmer)"),
    (0x1800, 0x18AF, u"蒙古文 (Mongolian)"),
    (0x18B0, 0x18FF, u"Cham"),
    (0x1900, 0x194F, u"Limbu"),
    (0x1950, 0x197F, u"德宏泰语 (Tai Le)"),
    (0x1980, 0x19DF, u"新傣仂语 (New Tai Lue)"),
    (0x19E0, 0x19FF, u"高棉语记号 (Kmer Symbols)"),
    (0x1A00, 0x1A1F, u"Buginese"),
    (0x1A20, 0x1A5F, u"Batak"),
    (0x1A80, 0x1AEF, u"Lanna"),
    (0x1B00, 0x1B7F, u"巴厘语 (Balinese)"),
    (0x1B80, 0x1BB0, u"巽他语 (Sundanese)"),
    (0x1BC0, 0x1BFF, u"Pahawh Hmong"),
    (0x1C00, 0x1C4F, u"雷布查语(Lepcha)"),
    (0x1C50, 0x1C7F, u"Ol Chiki"),
    (0x1C80, 0x1CDF, u"曼尼普尔语 (Meithei/Manipuri)"),
    (0x1D00, 0x1D7F, u"语音学扩展 (Phonetic Extensions)"),
    (0x1D80, 0x1DBF, u"语音学扩展补充 (Phonetic Extensions Supplement)"),
    (0x1DC0, 0x1DFF, u"结合用读音符号补充 (Combining Diacritics Marks Supplement)"),
    (0x1E00, 0x1EFF, u"拉丁文扩充附加 (Latin Extended Additional)"),
    (0x1F00, 0x1FFF, u"希腊语扩充 (Greek Extended)"),
    (0x2000, 0x206F, u"常用标点 (General Punctuation)"),
    (0x2070, 0x209F, u"上标及下标 (Superscripts and Subscripts)"),
    (0x20A0, 0x20CF, u"货币符号 (Currency Symbols)"),
    (0x20D0, 0x20FF, u"组合用记号 (Combining Diacritics Marks for Symbols)"),
    (0x2100, 0x214F, u"字母式符号 (Letterlike Symbols)"),
    (0x2150, 0x218F, u"数字形式 (Number Form)"),
    (0x2190, 0x21FF, u"箭头 (Arrows)"),
    (0x2200, 0x22FF, u"数学运算符 (Mathematical Operator)"),
    (0x2300, 0x23FF, u"杂项工业符号 (Miscellaneous Technical)"),
    (0x2400, 0x243F, u"控制图片 (Control Pictures)"),
    (0x2440, 0x245F, u"光学识别符 (Optical Character Recognition)"),
    (0x2460, 0x24FF, u"封闭式字母数字 (Enclosed Alphanumerics)"),
    (0x2500, 0x257F, u"制表符 (Box Drawing)"),
    (0x2580, 0x259F, u"方块元素 (Block Element)"),
    (0x25A0, 0x25FF, u"几何图形 (Geometric Shapes)"),
    (0x2600, 0x26FF, u"杂项符号 (Miscellaneous Symbols)"),
    (0x2700, 0x27BF, u"印刷符号 (Dingbats)"),
    (0x27C0, 0x27EF, u"杂项数学符号, 0xA (Miscellaneous Mathematical Symbols, 0xA)"),
    (0x27F0, 0x27FF, u"追加箭头, 0xA (Supplemental Arrows, 0xA)"),
    (0x2800, 0x28FF, u"盲文点字模型 (Braille Patterns)"),
    (0x2900, 0x297F, u"追加箭头, 0xB (Supplemental Arrows, 0xB)"),
    (0x2980, 0x29FF, u"杂项数学符号, 0xB (Miscellaneous Mathematical Symbols, 0xB)"),
    (0x2A00, 0x2AFF, u"追加数学运算符 (Supplemental Mathematical Operator)"),
    (0x2B00, 0x2BFF, u"杂项符号和箭头 (Miscellaneous Symbols and Arrows)"),
    (0x2C00, 0x2C5F, u"格拉哥里字母 (Glagolitic)"),
    (0x2C60, 0x2C7F, u"拉丁文扩展, 0xC (Latin Extended, 0xC)"),
    (0x2C80, 0x2CFF, u"古埃及语 (Coptic)"),
    (0x2D00, 0x2D2F, u"格鲁吉亚语补充 (Georgian Supplement)"),
    (0x2D30, 0x2D7F, u"提非纳文 (Tifinagh)"),
    (0x2D80, 0x2DDF, u"埃塞俄比亚语扩展 (Ethiopic Extended)"),
    (0x2E00, 0x2E7F, u"追加标点 (Supplemental Punctuation)"),
    (0x2E80, 0x2EFF, u"CJK 部首补充 (CJK Radicals Supplement)"),
    (0x2F00, 0x2FDF, u"康熙字典部首 (Kangxi Radicals)"),
    (0x2FF0, 0x2FFF, u"表意文字描述符 (Ideographic Description Characters)"),
    (0x3000, 0x303F, u"CJK 符号和标点 (CJK Symbols and Punctuation)"),
    (0x3040, 0x309F, u"日文平假名 (Hiragana)"),
    (0x30A0, 0x30FF, u"日文片假名 (Katakana)"),
    (0x3100, 0x312F, u"注音字母 (Bopomofo)"),
    (0x3130, 0x318F, u"朝鲜文兼容字母 (Hangul Compatibility Jamo)"),
    (0x3190, 0x319F, u"象形字注释标志 (Kanbun)"),
    (0x31A0, 0x31BF, u"注音字母扩展 (Bopomofo Extended)"),
    (0x31C0, 0x31EF, u"CJK 笔画 (CJK Strokes)"),
    (0x31F0, 0x31FF, u"日文片假名语音扩展 (Katakana Phonetic Extensions)"),
    (0x3200, 0x32FF, u"封闭式 CJK 文字和月份 (Enclosed CJK Letters and Months)"),
    (0x3300, 0x33FF, u"CJK 兼容 (CJK Compatibility)"),
    (0x3400, 0x4DBF, u"CJK 统一表意符号扩展 A (CJK Unified Ideographs Extension A)"),
    (0x4DC0, 0x4DFF, u"易经六十四卦符号 (Yijing Hexagrams Symbols)"),
    (0x4E00, 0x9FBF, u"CJK 统一表意符号 (CJK Unified Ideographs)"),
    (0xA000, 0xA48F, u"彝文音节 (Yi Syllables)"),
    (0xA490, 0xA4CF, u"彝文字根 (Yi Radicals)"),
    (0xA500, 0xA61F, u"Vai"),
    (0xA660, 0xA6FF, u"统一加拿大土著语音节补充 (Unified Canadian Aboriginal Syllabics Supplement)"),
    (0xA700, 0xA71F, u"声调修饰字母 (Modifier Tone Letters)"),
    (0xA720, 0xA7FF, u"拉丁文扩展, 0xD (Latin Extended, 0xD)"),
    (0xA800, 0xA82F, u"Syloti Nagri"),
    (0xA840, 0xA87F, u"八思巴字 (Phags, 0xpa)"),
    (0xA880, 0xA8DF, u"Saurashtra"),
    (0xA900, 0xA97F, u"爪哇语 (Javanese)"),
    (0xA980, 0xA9DF, u"Chakma"),
    (0xAA00, 0xAA3F, u"Varang Kshiti"),
    (0xAA40, 0xAA6F, u"Sorang Sompeng"),
    (0xAA80, 0xAADF, u"Newari"),
    (0xAB00, 0xAB5F, u"越南傣语 (Vi?t Thái)"),
    (0xAB80, 0xABA0, u"Kayah Li"),
    (0xAC00, 0xD7AF, u"朝鲜文音节 (Hangul Syllables)"),
    (0xD800, 0xDBFF, u"High, 0xhalf zone of UTF, 0x16"),
    (0xDC00, 0xDFFF, u"Low, 0xhalf zone of UTF, 0x16"),
    (0xE000, 0xF8FF, u"自行使用區域 (Private Use Zone)"),
    (0xF900, 0xFAFF, u"CJK 兼容象形文字 (CJK Compatibility Ideographs)"),
    (0xFB00, 0xFB4F, u"字母表達形式 (Alphabetic Presentation Form)"),
    (0xFB50, 0xFDFF, u"阿拉伯表達形式A (Arabic Presentation Form, 0xA)"),
    (0xFE00, 0xFE0F, u"变量选择符 (Variation Selector)"),
    (0xFE10, 0xFE1F, u"竖排形式 (Vertical Forms)"),
    (0xFE20, 0xFE2F, u"组合用半符号 (Combining Half Marks)"),
    (0xFE30, 0xFE4F, u"CJK 兼容形式 (CJK Compatibility Forms)"),
    (0xFE50, 0xFE6F, u"小型变体形式 (Small Form Variants)"),
    (0xFE70, 0xFEFF, u"阿拉伯表達形式B (Arabic Presentation Form, 0xB)"),
    (0xFF00, 0xFFEF, u"半型及全型形式 (Halfwidth and Fullwidth Form)"),
    (0xFFF0, 0xFFFF, u"特殊 (Specials)"),
]


def get_unicode_charset_entry(code):
    for item in unicode_charset_map:
        if item[0] <= code <= item[1]:
            return item
    return None


class CMapError(Exception):
    pass


##  CMapBase
##
class CMapBase(object):

    debug = 0

    def __init__(self, **kwargs):
        self.attrs = kwargs.copy()
        return

    def is_vertical(self):
        return self.attrs.get('WMode', 0) != 0

    def set_attr(self, k, v):
        self.attrs[k] = v
        return

    def add_code2cid(self, code, cid):
        return

    def add_cid2unichr(self, cid, code):
        return

    def use_cmap(self, cmap):
        return


##  CMap
##
class CMap(CMapBase):

    def __init__(self, **kwargs):
        CMapBase.__init__(self, **kwargs)
        self.code2cid = {}
        return

    def __repr__(self):
        return '<CMap: %s>' % self.attrs.get('CMapName')

    def use_cmap(self, cmap):
        assert isinstance(cmap, CMap)

        def copy(dst, src):
            for (k, v) in src.iteritems():
                if isinstance(v, dict):
                    d = {}
                    dst[k] = d
                    copy(d, v)
                else:
                    dst[k] = v
        copy(self.code2cid, cmap.code2cid)
        return

    def decode(self, code):
        if self.debug:
            logging.debug('decode: %r, %r' % (self, code))
        d = self.code2cid
        for c in code:
            c = ord(c)
            if c in d:
                d = d[c]
                if isinstance(d, int):
                    yield d
                    d = self.code2cid
            else:
                d = self.code2cid
        return

    def dump(self, out=sys.stdout, code2cid=None, code=None):
        if code2cid is None:
            code2cid = self.code2cid
            code = ()
        for (k, v) in sorted(code2cid.iteritems()):
            c = code+(k,)
            if isinstance(v, int):
                out.write('code %r = cid %d\n' % (c, v))
            else:
                self.dump(out=out, code2cid=v, code=c)
        return


##  IdentityCMap
##
class IdentityCMap(CMapBase):

    def decode(self, code):
        n = len(code)//2
        if n:
            return struct.unpack('>%dH' % n, code)
        else:
            return ()


##  UnicodeMap
##
class UnicodeMap(CMapBase):

    def __init__(self, **kwargs):
        CMapBase.__init__(self, **kwargs)
        self.cid2unichr = {}
        return

    def __repr__(self):
        return '<UnicodeMap: %s>' % self.attrs.get('CMapName')

    def get_unichr(self, cid):
        if self.debug:
            logging.debug('get_unichr: %r, %r' % (self, cid))
        return self.cid2unichr[cid]

    def dump(self, out=sys.stdout):
        for (k, v) in sorted(self.cid2unichr.iteritems()):
            out.write('cid %d = unicode %r\n' % (k, v))
        return


##  FileCMap
##
class FileCMap(CMap):

    def add_code2cid(self, code, cid):
        assert isinstance(code, str) and isinstance(cid, int)
        d = self.code2cid
        for c in code[:-1]:
            c = ord(c)
            if c in d:
                d = d[c]
            else:
                t = {}
                d[c] = t
                d = t
        c = ord(code[-1])
        d[c] = cid
        return


##  FileUnicodeMap
##
class FileUnicodeMap(UnicodeMap):

    def __init__(self, **kwargs):
        UnicodeMap.__init__(self, **kwargs)
        self.bfranges = []

    def add_cid2unichr(self, cid, code):
        assert isinstance(cid, int)
        if isinstance(code, PSLiteral):
            # Interpret as an Adobe glyph name.
            self.cid2unichr[cid] = name2unicode(code.name)
        elif isinstance(code, str):
            # Interpret as UTF-16BE.
            self.cid2unichr[cid] = unicode(code, 'UTF-16BE', 'ignore')
        elif isinstance(code, int):
            self.cid2unichr[cid] = unichr(code)
        else:
            raise TypeError(code)
        return

    def get_nearest_bfrange(self, cid):
        # only extend cmap in same char-set
        # (cid_start, cid_end, target_ucode, off)
        prev = None
        for item in self.bfranges:
            if cid < item[0]:
                same_cur = self.is_same_charset(cid, item)
                same_prev = False if not prev else self.is_same_charset(cid, prev)
                if same_prev and same_cur:
                    return prev if cid - prev[1] < item[0]-cid else item
                elif same_prev:
                    return prev
                elif same_cur:
                    return item
                return None
            prev = item

        if self.bfranges and self.is_same_charset(cid, self.bfranges[-1]):
            return self.bfranges[-1]
        return None

    def is_same_charset(self, cid, bfrangeitem):
        charset = get_unicode_charset_entry(cid + bfrangeitem[3])
        if charset and charset[0] <= bfrangeitem[2] <= charset[1]:
            return True
        return False

    def get_unichr(self, cid):
        if cid not in self.cid2unichr:
            item = self.get_nearest_bfrange(cid)
            if item:
                self.add_cid2unichr(cid, cid+item[3])
                logger.info("CMap-bfrange: %s, mapping undefined_char 0x%x(%d) to 0x%x: %s" % ("{}".format(item), cid, cid, cid+item[3], unichr(cid+item[3])))
            pass

        return UnicodeMap.get_unichr(self, cid)


##  PyCMap
##
class PyCMap(CMap):

    def __init__(self, name, module):
        CMap.__init__(self, CMapName=name)
        self.code2cid = module.CODE2CID
        if module.IS_VERTICAL:
            self.attrs['WMode'] = 1
        return


##  PyUnicodeMap
##
class PyUnicodeMap(UnicodeMap):

    def __init__(self, name, module, vertical):
        UnicodeMap.__init__(self, CMapName=name)
        if vertical:
            self.cid2unichr = module.CID2UNICHR_V
            self.attrs['WMode'] = 1
        else:
            self.cid2unichr = module.CID2UNICHR_H
        return


##  CMapDB
##
class CMapDB(object):

    _cmap_cache = {}
    _umap_cache = {}

    class CMapNotFound(CMapError):
        pass

    @classmethod
    def _load_data(klass, name):
        filename = '%s.pickle.gz' % name
        logger.info('loading: %r' % name)
        cmap_paths = (os.environ.get('CMAP_PATH', '/usr/share/pdfminer/'),
                      os.path.join(os.path.dirname(__file__), 'cmap'),)
        for directory in cmap_paths:
            path = os.path.join(directory, filename)
            if os.path.exists(path):
                gzfile = gzip.open(path)
                try:
                    return type(str(name), (), pickle.loads(gzfile.read()))
                finally:
                    gzfile.close()
        else:
            raise CMapDB.CMapNotFound(name)

    @classmethod
    def get_cmap(klass, name):
        if name == 'Identity-H':
            return IdentityCMap(WMode=0)
        elif name == 'Identity-V':
            return IdentityCMap(WMode=1)
        try:
            return klass._cmap_cache[name]
        except KeyError:
            pass
        data = klass._load_data(name)
        klass._cmap_cache[name] = cmap = PyCMap(name, data)
        return cmap

    @classmethod
    def get_unicode_map(klass, name, vertical=False):
        try:
            return klass._umap_cache[name][vertical]
        except KeyError:
            pass
        data = klass._load_data('to-unicode-%s' % name)
        klass._umap_cache[name] = umaps = [PyUnicodeMap(name, data, v) for v in (False, True)]
        return umaps[vertical]


##  CMapParser
##
class CMapParser(PSStackParser):

    def __init__(self, cmap, fp):
        PSStackParser.__init__(self, fp)
        self.cmap = cmap
        # some ToUnicode maps don't have "begincmap" keyword.
        self._in_cmap = True

        self.cmap_bfrange_items = []
        self.drop_bfrange_items = []
        return

    def run(self):
        try:
            self.nextobject()
        except PSEOF:
            pass

        # fixup cmap in ill-pdf, by janbox on 20180524
        self.fixup_cmaps()
        return

    KEYWORD_BEGINCMAP = KWD(b'begincmap')
    KEYWORD_ENDCMAP = KWD(b'endcmap')
    KEYWORD_USECMAP = KWD(b'usecmap')
    KEYWORD_DEF = KWD(b'def')
    KEYWORD_BEGINCODESPACERANGE = KWD(b'begincodespacerange')
    KEYWORD_ENDCODESPACERANGE = KWD(b'endcodespacerange')
    KEYWORD_BEGINCIDRANGE = KWD(b'begincidrange')
    KEYWORD_ENDCIDRANGE = KWD(b'endcidrange')
    KEYWORD_BEGINCIDCHAR = KWD(b'begincidchar')
    KEYWORD_ENDCIDCHAR = KWD(b'endcidchar')
    KEYWORD_BEGINBFRANGE = KWD(b'beginbfrange')
    KEYWORD_ENDBFRANGE = KWD(b'endbfrange')
    KEYWORD_BEGINBFCHAR = KWD(b'beginbfchar')
    KEYWORD_ENDBFCHAR = KWD(b'endbfchar')
    KEYWORD_BEGINNOTDEFRANGE = KWD(b'beginnotdefrange')
    KEYWORD_ENDNOTDEFRANGE = KWD(b'endnotdefrange')
    
    def do_keyword(self, pos, token):
        if token is self.KEYWORD_BEGINCMAP:
            self._in_cmap = True
            self.popall()
            return
        elif token is self.KEYWORD_ENDCMAP:
            self._in_cmap = False
            return
        if not self._in_cmap:
            return
        #
        if token is self.KEYWORD_DEF:
            try:
                ((_, k), (_, v)) = self.pop(2)
                self.cmap.set_attr(literal_name(k), v)
            except PSSyntaxError:
                pass
            return

        if token is self.KEYWORD_USECMAP:
            try:
                ((_, cmapname),) = self.pop(1)
                self.cmap.use_cmap(CMapDB.get_cmap(literal_name(cmapname)))
            except PSSyntaxError:
                pass
            except CMapDB.CMapNotFound:
                pass
            return

        if token is self.KEYWORD_BEGINCODESPACERANGE:
            self.popall()
            return
        if token is self.KEYWORD_ENDCODESPACERANGE:
            self.popall()
            return

        if token is self.KEYWORD_BEGINCIDRANGE:
            self.popall()
            return
        if token is self.KEYWORD_ENDCIDRANGE:
            objs = [obj for (__, obj) in self.popall()]
            for (s, e, cid) in choplist(3, objs):
                if (not isinstance(s, str) or not isinstance(e, str) or
                   not isinstance(cid, int) or len(s) != len(e)):
                    continue
                sprefix = s[:-4]
                eprefix = e[:-4]
                if sprefix != eprefix:
                    continue
                svar = s[-4:]
                evar = e[-4:]
                s1 = nunpack(svar)
                e1 = nunpack(evar)
                vlen = len(svar)
                #assert s1 <= e1
                for i in xrange(e1-s1+1):
                    x = sprefix+struct.pack('>L', s1+i)[-vlen:]
                    self.cmap.add_code2cid(x, cid+i)
            return

        if token is self.KEYWORD_BEGINCIDCHAR:
            self.popall()
            return
        if token is self.KEYWORD_ENDCIDCHAR:
            objs = [obj for (__, obj) in self.popall()]
            for (cid, code) in choplist(2, objs):
                if isinstance(code, str) and isinstance(cid, str):
                    self.cmap.add_code2cid(code, nunpack(cid))
            return

        if token is self.KEYWORD_BEGINBFRANGE:
            self.popall()
            return
        if token is self.KEYWORD_ENDBFRANGE:
            objs = [obj for (__, obj) in self.popall()]
            for (s, e, code) in choplist(3, objs):
                if (not isinstance(s, str) or not isinstance(e, str) or
                   len(s) != len(e)):
                        continue
                s1 = nunpack(s)
                e1 = nunpack(e)
                #assert s1 <= e1
                if isinstance(code, list):
                    for i in xrange(e1-s1+1):
                        self.cmap.add_cid2unichr(s1+i, code[i])
                else:
                    var = code[-4:]
                    base = nunpack(var)
                    prefix = code[:-4]
                    vlen = len(var)
                    e2 = self.verify_char_set(s1, e1, base)
                    if e2:
                        for i in xrange(e2-s1+1):
                            x = prefix+struct.pack('>L', base+i)[-vlen:]
                            self.cmap.add_cid2unichr(s1+i, x)
                        self.cmap_bfrange_items.append((s1, e2, base, base-s1))
                    else:
                        self.drop_bfrange_items.append((s1, e1, base, base-s1))
            return

        if token is self.KEYWORD_BEGINBFCHAR:
            self.popall()
            return
        if token is self.KEYWORD_ENDBFCHAR:
            objs = [obj for (__, obj) in self.popall()]
            for (cid, code) in choplist(2, objs):
                if isinstance(cid, str) and isinstance(code, str):
                    self.cmap.add_cid2unichr(nunpack(cid), code)
            return

        if token is self.KEYWORD_BEGINNOTDEFRANGE:
            self.popall()
            return
        if token is self.KEYWORD_ENDNOTDEFRANGE:
            self.popall()
            return

        self.push((pos, token))
        return

    def fixup_cmaps(self):
        if self.drop_bfrange_items:
            logger.warning("drop unexpected bfrange items: {}".format(self.drop_bfrange_items))

        if not self.cmap_bfrange_items:
            return

        # (s1, e1, base, off)
        merged_bfranges = self.fill_cmap_by_ranges(self.cmap_bfrange_items, True)

        if len(merged_bfranges) == len(self.cmap_bfrange_items):
            return

        # drop cross-range. merge small_range to large_range
        results_bfranges = []
        for item in merged_bfranges:
            matched = self.is_subset_of_ranges(merged_bfranges, item)
            if not matched:
                results_bfranges.append(item)

        if len(results_bfranges) != len(merged_bfranges):
            final_bfranges = self.fill_cmap_by_ranges(results_bfranges, True)
        else:
            final_bfranges = results_bfranges

        self.cmap.bfranges = sorted(final_bfranges, key=lambda x: x[0])

        self.cmap_bfrange_items = []
        return

    def fill_cmap_by_ranges(self, bfranges, add_to_map=True):
        result_bfranges = []
        last_merged = None
        prev = None
        for item in sorted(bfranges, key=lambda x: x[0]):
            if prev:
                # check prev and item are continues-range, and with equal-offset
                if item[2]-item[0] == prev[2]-prev[0]:
                    # print "prev={}, item={}".format(prev, item)
                    off = item[2] - item[0]
                    if add_to_map:
                        for i in range(prev[1]+1, item[0], 1):
                            self.cmap.add_cid2unichr(i, i + off)
                            pass
                    last_merged = (last_merged[0], item[1], last_merged[2], off)
                else:
                    result_bfranges.append(last_merged)
                    last_merged = item
            else:
                last_merged = item
            prev = item
        if last_merged:
            result_bfranges.append(last_merged)

        return result_bfranges

    def is_subset_of_ranges(self, bfranges, range):
        code_s = range[2]
        code_e = range[2] + range[1] - range[0]
        for item in bfranges:
            # skip itself
            if item == range:
                continue
            if code_s >= item[2] and code_e <= item[2] + item[1] - item[0]:
                return item
        return None

    def verify_char_set(self, s1, e1, base):
        # verify if s1=>base, e1=>base+e1-s1 are in same char-set
        # caller will discard cmap-entry if verify_char_set return False
        item = get_unicode_charset_entry(base)
        if item:
            if item[1] - base + s1 < e1:
                return s1
            return e1

        return None


# test
def main(argv):
    args = argv[1:]
    for fname in args:
        fp = file(fname, 'rb')
        cmap = FileUnicodeMap()
        #cmap = FileCMap()
        CMapParser(cmap, fp).run()
        fp.close()
        cmap.dump()
    return

if __name__ == '__main__':
    sys.exit(main(sys.argv))
