# -*- Mode: Python; coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Stoqdrivers
## Copyright (C) 2016 Stoq Tecnologia <http://stoq.link>
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

# Based on python-escpos's escpos.escpos.Escpos:
#
# https://github.com/python-escpos/python-escpos/blob/master/src/escpos/escpos.py

#
# Basic Characters
#

ESC = b'\x1b'  # Escape
GS = b'\x1d'  # Group Separator

#
# Charcodes
#

CHARCODES = {
    'USA': ['cp437', ESC + b'\x74\x00'],            # USA: Standard Europe
    'JIS': ['cp932', ESC + b'\x74\x01'],            # Japanese Katakana
    'MULTILINGUAL': ['cp850', ESC + b'\x74\x02'],   # Multilingual
    'PORTUGUESE': ['cp860', ESC + b'\x74\x03'],     # Portuguese
    'CA_FRENCH': ['cp863', ESC + b'\x74\x04'],      # Canadian-French
    'NORDIC': ['cp865', ESC + b'\x74\x05'],         # Nordic
    'WEST_EUROPE': ['latin_1', ESC + b'\x74\x06'],  # Simplified Kanji, Hirakana
    'GREEK': ['cp737', ESC + b'\x74\x07'],          # Simplified Kanji
    'HEBREW': ['cp862', ESC + b'\x74\x08'],         # Simplified Kanji
    'WPC1252': ['cp1252', ESC + b'\x74\x11'],       # Western European Windows Code Set
    'CIRILLIC2': ['cp866', ESC + b'\x74\x12'],      # Cirillic #2
    'LATIN2': ['cp852', ESC + b'\x74\x13'],         # Latin 2
    'EURO': ['cp858', ESC + b'\x74\x14'],           # Euro
    'THAI42': ['cp874', ESC + b'\x74\x15'],         # Thai character code 42
    'THAI11': ['cp874', ESC + b'\x74\x16'],         # Thai character code 11
    'THAI13': ['cp874', ESC + b'\x74\x17'],         # Thai character code 13
    'THAI14': ['cp874', ESC + b'\x74\x18'],         # Thai character code 14
    'THAI16': ['cp874', ESC + b'\x74\x19'],         # Thai character code 16
    'THAI17': ['cp874', ESC + b'\x74\x1a'],         # Thai character code 17
    'THAI18': ['cp874', ESC + b'\x74\x1b'],         # Thai character code 18
}

#
# Font Commands
#

FONT_A = ESC + b'M0'
FONT_B = ESC + b'M1'

#
# Text
#

TXT_ALIGN_LT = ESC + b'\x61\x00'  # Left justification
TXT_ALIGN_CT = ESC + b'\x61\x01'  # Centering

TXT_BOLD_OFF = ESC + b'\x45\x00'  # Bold font OFF
TXT_BOLD_ON = ESC + b'\x45\x01'  # Bold font ON

#
# Barcode
#

BARCODE_HEIGHT = GS + b'h'  # Barcode Height [1-255]
BARCODE_WIDTH = GS + b'w'  # Barcode Width  [2-6]

BARCODE_FONT_A = GS + b'f' + b'\x00'  # Font A for HRI barcode chars
BARCODE_FONT_B = GS + b'f' + b'\x01'  # Font B for HRI barcode chars

BARCODE_TXT_OFF = GS + b'H' + b'\x00'  # HRI barcode chars OFF
BARCODE_TXT_ABV = GS + b'H' + b'\x01'  # HRI barcode chars above
BARCODE_TXT_BLW = GS + b'H' + b'\x02'  # HRI barcode chars below
BARCODE_TXT_BTH = GS + b'H' + b'\x03'  # HRI both above and below

BARCODE_CODE93 = GS + b'k' + b'H'  # Use a CODE93 Barcode

#
# Line Feed
#

LINE_FEED_RESET = ESC + b'2'
LINE_FEED_SET = ESC + b'3'

#
# Misc
#

PAPER_FULL_CUT = GS + b'V\x00'  # Full Paper Cut


class EscPosMixin(object):
    #: How many line feeds should be done before cutting the paper
    cut_line_feeds = 4

    #: Which charcode to be used as default
    charcode = None

    #: The default font
    default_font = FONT_B

    #: The maximum number of characters that fit a line
    max_characters = 64

    #: The maximum number of characters that fit a barcode
    max_barcode_characters = 27

    def __init__(self, columns=32, charcode=None):
        """
        Initialize ESCPOS Printer

        :param columns: Number of text columns on the printer (Default: 32)
        """
        self.columns = columns
        self.set_charcode(charcode)

    def set_charcode(self, code):
        """
        Set character code table

        Send the control command to the printer and will encode any text sent
        to printing with the selected charcode.

        :param code: Name of the charcode (e.g.: 'latin1')
        """
        if code is None:
            self.codepage = None
            return

        # Normalize everything to uppercase
        codepage, charcode = CHARCODES[code.upper()]
        self.codepage = codepage
        self.write(charcode)

    #
    # INonFiscalPrinter Methods
    #

    def centralize(self):
        """ Centralize the text to be sent to coupon. """
        self.write(TXT_ALIGN_CT)

    def descentralize(self):
        """ Descentralize the text to be sent to coupon. """
        self.write(TXT_ALIGN_LT)

    def set_bold(self):
        """ The sent text will be appear in bold. """
        self.write(TXT_BOLD_ON)

    def unset_bold(self):
        """ Remove the bold option. """
        self.write(TXT_BOLD_OFF)

    def print_line(self, text):
        """ Performs a line break to the given text. """
        self.print_inline(text + '\n')

    def print_inline(self, text):
        """ Print a given text in a unique line. """
        # Do nothing for empty texts
        if not text:
            return

        # Make sure the text is unicode
        if not isinstance(text, unicode):
            text = unicode(text)

        # Encode the text with the correct codepage
        if self.codepage:
            text = text.encode(self.codepage)

        # Then, finally write the text
        self.write(self.default_font)
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
            self.print_line('')
            self.print_barcode(code[length:])
            return

        # Set Width and Height
        self.write(BARCODE_HEIGHT + chr(80))
        self.write(BARCODE_WIDTH + chr(2))

        # Other settings
        self.write(BARCODE_FONT_A)
        self.write(BARCODE_TXT_OFF)

        # Then write the code
        self.write(BARCODE_CODE93 + chr(len(code)) + code.encode())

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
        self.print_inline('\n' * self.cut_line_feeds)
        self.write(PAPER_FULL_CUT)
