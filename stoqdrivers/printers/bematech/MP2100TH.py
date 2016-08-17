# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2015 Async Open Source <http://www.async.com.br>
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
from zope.interface import implements

from stoqdrivers.interfaces import INonFiscalPrinter
from stoqdrivers.serialbase import SerialBase
from stoqdrivers.utils import GRAPHICS_8BITS, GRAPHICS_24BITS, matrix2graphics

# FIXME: probably all those commands should be defined on the
# class itself to allow subclasses to overwrite them easily
ESC = '\x1b'
GS = '\x1d'

LINE_FEED = ESC + 'A\x00'
CENTRALIZE = ESC + 'a\x01'
DESCENTRALIZE = ESC + 'a\x00'
CONDENSED_MODE = ESC + '\x0f'
NORMAL_MODE = ESC + 'H'
SET_BOLD = ESC + 'E'
UNSET_BOLD = ESC + 'F'
BARCODE_128 = GS + 'kn'


class MP2100TH(SerialBase):
    implements(INonFiscalPrinter)

    supported = True
    model_name = "Bematech MP2100 TH"
    max_characters = 64

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

    def __init__(self, port, consts=None):
        self._is_bold = False
        self._is_centralized = False
        SerialBase.__init__(self, port)
        self.write(CONDENSED_MODE)

    #
    #  INonFiscalPrinter
    #

    def centralize(self):
        if self._is_centralized:
            return
        self.write(CENTRALIZE)
        self._is_centralized = True

    def descentralize(self):
        if not self._is_centralized:
            return
        self.write(DESCENTRALIZE)
        self._is_centralized = False

    def set_bold(self):
        if self._is_bold:
            return
        self.write(SET_BOLD)
        self._is_bold = True

    def unset_bold(self):
        if not self._is_bold:
            return
        self.write(UNSET_BOLD)
        self._is_bold = False

    def print_line(self, data):
        self.write(data + '\n')

    def print_inline(self, data):
        self.write(data)

    def print_barcode(self, code):
        # Change the height
        self.write(GS + '\x68%s' % chr(120))
        # Normal width
        self.write(GS + '\x77\x02')
        # No HRI (human readable information)
        self.write(GS + '\x48\x00')

        cmd = GS + '\x6b\x49%s%s' % (chr(len(code)), code)
        self.write(cmd)

    def print_qrcode(self, code):
        qr = qrcode.QRCode(version=1, border=4)
        qr.add_data(code)
        self.write('\x00')
        self._print_matrix(qr.get_matrix())

    def cut_paper(self):
        # FIXME: Ensure the paper is safely out of the paper-cutter before
        #        executing the cut.
        self.print_inline('\n' * 2)
        self.write(ESC + '\x6d')

    #
    #  Private
    #

    def _print_matrix(self, matrix):
        max_cols = self.GRAPHICS_MAX_COLS[self.GRAPHICS_API]
        cmd = self.GRAPHICS_CMD[self.GRAPHICS_API]

        for line, line_len in matrix2graphics(self.GRAPHICS_API, matrix,
                                              max_cols, self.GRAPHICS_MULTIPLIER):
            assert line_len <= max_cols
            n2 = 0
            n1 = line_len
            # line_len = n1 + n2 * 256
            while n1 >= 256:
                n2 += 1
                n1 -= 256

            self.write(cmd % (chr(n1), chr(n2), line))
            self.write(LINE_FEED)
