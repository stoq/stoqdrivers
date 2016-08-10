# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2016 Async Open Source <http://www.async.com.br>
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

from zope.interface import implements

from stoqdrivers.interfaces import INonFiscalPrinter
from stoqdrivers.serialbase import SerialBase

NORMAL_FONT = '\x1b\x4d\x00'
CONDENSED_MODE = '\x1b\x4d\x01'

CENTRALIZE = '\x1b\x61\x01'
DESCENTRALIZE = '\x1b\x61\x00'
SET_BOLD = '\x1b\x45\x01'
UNSET_BOLD = '\x1b\x45\x00'


class I9(SerialBase):
    implements(INonFiscalPrinter)

    supported = True
    model_name = "Elgin I9"
    # FIXME: Check the real max number of characters
    max_characters = 57

    def __init__(self, port, consts=None):
        self._is_bold = False
        self._is_centralized = False
        SerialBase.__init__(self, port)
        self.write(NORMAL_FONT)
        self.write(CONDENSED_MODE)

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
        """
        Prints the barcode

        Parameters:
            m - barcode type
            n - length (2 <= n <= 255)
            d1 and d2 represents the symbology used on barcode
                d2: 65 - A / 66 - B / 67 - C
            data - code with 22 digits used to generate the barcode
        """

        # Height
        self.write('\x1d\x68%s' % chr(80))
        # Width
        self.write('\x1d\x77%s' % chr(2))

        # 1D 6B m(73) n(67) d1(123) d2(65) data
        cmd = '\x1d\x6bI%s{A%s'

        # The size of parameters d1 and d2 must be added to the final size of barcode
        len_data = 24
        for i in range(0, len(code), 22):
            self.write(cmd % (chr(len_data), code[i:i + 22]))

        self.write('\x0A')

    def print_qrcode(self, code):
        """
        Prints the QR code

        Parameters:
            PL and PH - defines (pL + pH * 256) for number of bytes according to
                        pH(cn, fn, and [parameters])
            cn - defines symbol type (48 - PDF417 and 49 - QR code)
            fn - defines the function
            parameters - specifies the process of each function
        """

        # QR code size - 1D 28 6B pl(3) ph(0) cn(49) fn(67) n(3)
        # 1 <= n <= 16
        self.write('\x1d\x28\x6b\x03\x00%s%s%s' % (chr(49), chr(67), chr(4)))

        # Level error correction - 1D 28 6B pl(3) ph(0) cn(49) fn(67) n(48)
        # 48 <= n <=51 (levels L, M, Q, H)
        self.write('\x1d\x28\x6b\x03\x00%s%s%s' % (chr(49), chr(69), chr(48)))

        # Store data in symbols storage area - 1D 28 6B pl ph cn(49) fn(80) m(48) data
        bytes_len = 3 + len(code)
        pl = chr(bytes_len & 0xff)
        ph = chr((bytes_len >> 8 & 0xff))
        cmd = '\x1d\x28\x6b%s%s%s%s%s%s' % (pl, ph, chr(49), chr(80), chr(48),
                                            code)
        self.write(cmd)

        # Print - 1D 28 6B pl(3) ph(0) cn(49) fn(81) m(48)
        self.write('\x1d\x28\x6b\x03\x00%s%s%s' % (chr(49), chr(81), chr(48)))

    def cut_paper(self):
        self.write('\x1d\x56%s' % chr(48))
