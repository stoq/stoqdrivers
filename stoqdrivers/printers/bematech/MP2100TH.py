# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2015-2019 Stoq Tecnologia <http://stoq.com.br>
## All rights reserved
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU Lesser General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., or visit: http://www.gnu.org/.
##
## Author(s): Stoq Team <stoq-devel@async.com.br>
##

import qrcode
from zope.interface import implementer
from stoqdrivers.exceptions import InvalidReplyException
from stoqdrivers.escpos import EscPosMixin, ESC, GS

from stoqdrivers.interfaces import INonFiscalPrinter
from stoqdrivers.serialbase import SerialBase
from stoqdrivers.utils import GRAPHICS_8BITS

SI = '\x0f'


@implementer(INonFiscalPrinter)
class MP2100TH(SerialBase, EscPosMixin):
    TXT_BOLD_ON = ESC + 'E'
    TXT_BOLD_OFF = ESC + 'F'

    FONT_REGULAR = ESC + 'H'
    FONT_CONDENSED = ESC + SI

    DOUBLE_HEIGHT_OFF = ESC + 'd0'
    DOUBLE_HEIGHT_ON = ESC + 'd1'
    PAPER_FULL_CUT = ESC + '\x6d'

    cut_line_feeds = 2
    max_characters = 67
    supported = True
    model_name = "Bematech MP2100 TH"
    charset = 'cp850'

    CHARSET_MAP = {
        'cp850': '\x32',
        'utf8': '\x38',
    }

    def __init__(self, port, consts=None):
        SerialBase.__init__(self, port)
        # Make sure the printer is in ESC/BEMA mode
        self.write(GS + '\xF9\x20\x00')
        EscPosMixin.__init__(self)

    #
    #  INonFiscalPrinter
    #

    def print_qrcode(self, code):
        qr = qrcode.QRCode(version=1, border=4)
        qr.add_data(code)
        self.write('\x00')
        self.print_matrix(qr.get_matrix())

    def separator(self):
        max_cols = self.GRAPHICS_MAX_COLS[self.GRAPHICS_API]
        if self.GRAPHICS_API == GRAPHICS_8BITS:
            # See matrix2graphics for more info on this
            max_cols = max_cols // 3
        self.print_matrix([[False] * max_cols, [False] * max_cols, [True] * max_cols])

    def open_drawer(self):
        # This is the number of milliseconds to activate the electrical signal.
        # In tests, 3 was enough for the drawer we have. 2 did not open it. We
        # have an example of a drawer that requires 9, so using that for now.
        self.write(ESC + 'v9')

    def is_drawer_open(self):
        # b1 is to enable the printer to report the drawer status, otherwise it will report the
        # paper status
        self.write(ESC + 'b1')
        self.write(b'\x05')
        out = self.read(1)
        try:
            data = ord(out[0])
        except IndexError:
            raise InvalidReplyException
        if self.inverted_drawer:
            return (data & 4) == 4
        else:
            return (data & 4) != 4

    def set_charset(self, charset='cp850'):
        self.charset = charset
        # Set charset - \x38 - Unicode \x32 - cp850
        self.write('\x1d\xf9\x37%s' % self.CHARSET_MAP[charset])

    def print_barcode(self, code):
        """Print a barcode

        Instead of using command GS + 'kH', which is defined on escpos mixin,
        this printer uses the command GS + 'kI'
        """
        # Change the height
        self.write(self.BARCODE_HEIGHT + chr(30))
        # Normal width
        self.write(self.BARCODE_WIDTH + chr(2))
        # No HRI (human readable information)
        self.write(self.BARCODE_TXT_OFF)

        cmd = GS + 'kI%s%s' % (chr(len(code)), code)
        self.write(cmd)

    #
    #  Private
    #

    def _setup_commandset(self, commset='\x30'):
        # ESC/BEMA = 0x30
        # ESC/POS = 0x31
        self.write('\x1d\xf9\x35%s' % commset)

    def _print_configuration(self):
        # Print configuration
        self.write('\x1d\xf9\x29\x30')
