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

from zope.interface import implements

from stoqdrivers.interfaces import INonFiscalPrinter
from stoqdrivers.serialbase import SerialBase

NORMAL_FONT = '\x1b\x21\x00\x00'

CONDENSED_MODE = '\x1b\x0F\x00'
CENTRALIZE = '\x1b\x6A\x01'
DESCENTRALIZE = '\x1b\x6A\x00'
SET_BOLD = '\x1b\x45\x00'
UNSET_BOLD = '\x1b\x46\x00'


class DR700(SerialBase):
    implements(INonFiscalPrinter)

    supported = True
    model_name = "Daruma DR 700"

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
        code_128 = chr(5)
        width = chr(2)
        height = chr(80)
        barcode_label = chr(0)
        self.write('\x1b\x62%s%s%s%s%s\x00' % (code_128, width, height,
                                               barcode_label, code))
        self.write('\x0A')

    def print_qrcode(self, code):
        bytes_len = len(code)
        min_size = chr(bytes_len >> 8)
        max_size = chr((bytes_len & 255) + 2)
        width = chr(3)
        # Correction level: auto
        correction = chr(0)
        self.write('\x1b\x81%s%s%s%s%s' % (max_size, min_size, width, correction, code))
        self.write('\x0A')

    def cut_paper(self):
        self.write('\x1b\x6d')
