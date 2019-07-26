# -*- Mode: Python; coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Stoqdrivers
## Copyright (C) 2016-2019 Stoq Tecnologia <http://stoq.com.br>
## All rights reserved
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
## USA.

from stoqdrivers.utils import encode_text, GRAPHICS_8BITS, GRAPHICS_24BITS, matrix2graphics

# Based on python-escpos's escpos.escpos.Escpos:
#
# https://github.com/python-escpos/python-escpos/blob/master/src/escpos/escpos.py

ESC = '\x1b'  # Escape
GS = '\x1d'  # Group Separator


class EscPosMixin(object):
    FONT_REGULAR = ESC + 'M0'
    FONT_CONDENSED = ESC + 'M1'

    TXT_ALIGN_LEFT = ESC + 'a\x00'  # Left justification
    TXT_ALIGN_CENTER = ESC + 'a\x01'  # Centering

    TXT_BOLD_OFF = ESC + 'E\x00'  # Bold font OFF
    TXT_BOLD_ON = ESC + 'E\x01'  # Bold font ON

    DOUBLE_HEIGHT_ON = ESC + 'G\x00'  # Double height character
    DOUBLE_HEIGHT_OFF = ESC + 'G\x01'  # Normal height character

    LINE_FEED = '\x0a'
    LINE_FEED_RESET = ESC + '2'
    LINE_FEED_SET = ESC + '3'

    BARCODE_HEIGHT = GS + 'h'  # Barcode Height [1-255]
    BARCODE_WIDTH = GS + 'w'  # Barcode Width  [2-6]
    BARCODE_FONT_REGULAR = GS + 'f' + '\x00'  # Font Regular for HRI barcode chars
    BARCODE_FONT_CONDENSED = GS + 'f' + '\x01'  # Font Condensed for HRI barcode chars
    BARCODE_TXT_OFF = GS + 'H' + '\x00'  # HRI barcode chars OFF
    BARCODE_TXT_ABV = GS + 'H' + '\x01'  # HRI barcode chars above
    BARCODE_TXT_BLW = GS + 'H' + '\x02'  # HRI barcode chars below
    BARCODE_TXT_BTH = GS + 'H' + '\x03'  # HRI both above and below
    BARCODE_CODE93 = GS + 'k' + 'H'  # Use a CODE93 Barcode

    PAPER_FULL_CUT = GS + 'V\x00'  # Full Paper Cut

    CHARSET_CMD = {
        'cp850': ESC + '\x74\x02',  # Multilingual

        'cp437': ESC + '\x74\x00',  # USA: Standard Europe
        'cp932': ESC + '\x74\x01',  # Japanese Katakana
        'cp860': ESC + '\x74\x03',  # Portuguese
        'cp863': ESC + '\x74\x04',  # Canadian-French
        'cp865': ESC + '\x74\x05',  # Nordic
        'latin1': ESC + '\x74\x06',  # Simplified Kanji, Hirakana
        'cp737': ESC + '\x74\x07',  # Simplified Kanji
        'cp862': ESC + '\x74\x08',  # Simplified Kanji
        'cp1252': ESC + '\x74\x11',  # Western European Windows Code Set
        'cp866': ESC + '\x74\x12',  # Cirillic #2
        'cp852': ESC + '\x74\x13',  # Latin 2
        'cp858': ESC + '\x74\x14',  # Euro

    }

    #: How many line feeds should be done before cutting the paper
    cut_line_feeds = 4

    #: The default font
    default_font = FONT_CONDENSED

    #: The maximum number of characters that fit a line
    max_characters = 64

    #: The maximum number of characters that fit a barcode
    max_barcode_characters = 27

    GRAPHICS_API = GRAPHICS_8BITS
    GRAPHICS_MULTIPLIER = 1
    GRAPHICS_MAX_COLS = {
        GRAPHICS_8BITS: 576,
        GRAPHICS_24BITS: 1728,
    }
    GRAPHICS_CMD = {
        GRAPHICS_8BITS: ESC + '\x4b%s%s%s',
        GRAPHICS_24BITS: ESC + '\x2a\x21%s%s%s',
    }

    def __init__(self, charset='cp850'):
        """
        Initialize ESCPOS Printer

        :param charset: the charset that the printer will be setup to use.
        """
        self.set_charset(charset)
        self.set_condensed()
        self.descentralize()
        self.unset_bold()
        self.unset_double_height()

    def set_charset(self, charset):
        """
        Set character set table

        Send the control command to the printer and will encode any text sent
        to printing with the selected charset.

        :param charset: Name of the charset (e.g.: 'latin1' or 'cp850')
        """
        self.charset = charset
        self.write(self.CHARSET_CMD[self.charset])

    #
    # INonFiscalPrinter Methods
    #

    def centralize(self):
        """ Centralize the text to be sent to coupon. """
        self.write(self.TXT_ALIGN_CENTER)

    def descentralize(self):
        """ Descentralize the text to be sent to coupon. """
        self.write(self.TXT_ALIGN_LEFT)

    def set_bold(self):
        """ The sent text will be appear in bold. """
        self.write(self.TXT_BOLD_ON)

    def unset_bold(self):
        """ Remove the bold option. """
        self.write(self.TXT_BOLD_OFF)

    def set_condensed(self):
        self.write(self.FONT_CONDENSED)

    def unset_condensed(self):
        self.write(self.FONT_REGULAR)

    def set_double_height(self):
        self.write(self.DOUBLE_HEIGHT_ON)

    def unset_double_height(self):
        self.write(self.DOUBLE_HEIGHT_OFF)

    def print_line(self, text: bytes):
        """ Performs a line break to the given text. """
        self.print_inline(text + b'\n')

    def print_inline(self, text):
        """ Print a given text in a unique line. """
        # Do nothing for empty texts
        if not text:
            return

        assert isinstance(text, bytes), text
        self.write(text)

    def print_barcode(self, code):
        """ Print a barcode representing the given code. """
        if not code:
            return

        # If the barcode size exceeds the maximum size in which the printer
        # could input in a single line, split it in two lines
        if len(code) > self.max_barcode_characters:
            # int() conversion is not actually required, but it makes the code
            # Python 3 ready.
            length = int(len(code) / 2)
            self.print_barcode(code[:length])
            self.print_line(b'')
            self.print_barcode(code[length:])
            return

        # Set Width and Height
        self.write(self.BARCODE_HEIGHT + chr(30))
        self.write(self.BARCODE_WIDTH + chr(2))

        # Other settings
        self.write(self.BARCODE_FONT_REGULAR)
        self.write(self.BARCODE_TXT_OFF)

        # Then write the code
        self.write(self.BARCODE_CODE93 + chr(len(code)) +
                   encode_text(code, self.charset))

    def print_qrcode(self, code):
        """ Prints the QR code """
        # Parameters:
        #     PL and PH - defines (pL + pH * 256) for number of bytes according
        #     to pH(cn, fn, and [parameters])
        #
        #     cn - defines symbol type (48 - PDF417 and 49 - QR code)
        #     fn - defines the function
        #     parameters - specifies the process of each function

        # Set QR Code module/size
        self.write(GS + '(k\x03\x00%s%s%s' % (chr(49), chr(67), chr(4)))

        # Level error correction - 1D 28 6B pl(3) ph(0) cn(49) fn(67) n(48)
        # Levels = (L, M, Q, H) => (48, 49, 50, 51)
        self.write(GS + '(k\x03\x00%s%s%s' % (chr(49), chr(69), chr(48)))

        # Store data in symbols storage area:
        # 1D 28 6B pl ph cn(49) fn(80) m(48) data
        bytes_len = 3 + len(code)
        pl = chr(bytes_len & 0xff)
        ph = chr((bytes_len >> 8 & 0xff))
        cmd = GS + '(k%s%s%s%s%s%s' % (pl, ph, chr(49), chr(80), chr(48), code)
        self.write(cmd)

        # Print - 1D 28 6B pl(3) ph(0) cn(49) fn(81) m(48)
        self.write(GS + '(k\x03\x00%s%s%s' % (chr(49), chr(81), chr(48)))

    def cut_paper(self):
        """ Performs a paper cutting. """
        # FIXME: Ensure the paper is safely out of the paper-cutter before
        #        executing the cut.
        self.print_inline(b'\n' * self.cut_line_feeds)
        self.write(self.PAPER_FULL_CUT)

    def print_matrix(self, matrix, api=None, linefeed=True, multiplier=None):
        multiplier = multiplier or self.GRAPHICS_MULTIPLIER
        if api is None:
            api = self.GRAPHICS_API

        max_cols = self.GRAPHICS_MAX_COLS[api]
        cmd = self.GRAPHICS_CMD[api]

        # Check that the given image fits properly with the api, and if not, try to increase the api
        line, line_len = next(matrix2graphics(api, matrix, max_cols, multiplier))
        if api == GRAPHICS_8BITS and line_len > max_cols:
            api = GRAPHICS_24BITS
            max_cols = self.GRAPHICS_MAX_COLS[api]
            cmd = self.GRAPHICS_CMD[api]

        # Change the space between lines to 0
        self.write(ESC + '3\x00')
        for line, line_len in matrix2graphics(api, matrix,
                                              max_cols, multiplier,
                                              centralized=False):
            assert line_len <= max_cols, (line_len, max_cols)
            n2 = 0
            n1 = line_len
            # line_len = n1 + n2 * 256
            while n1 >= 256:
                n2 += 1
                n1 -= 256

            self.write(cmd % (chr(n1), chr(n2), line))
            if linefeed:
                self.write(self.LINE_FEED)

        # Change the space between lines to default
        self.write(ESC + '2')
