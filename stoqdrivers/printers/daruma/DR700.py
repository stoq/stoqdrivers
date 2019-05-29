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

from zope.interface import implementer

from stoqdrivers.interfaces import INonFiscalPrinter
from stoqdrivers.serialbase import SerialBase

ESC = '\x1b'
SI = '\x0f'
DC2 = '\x12'

NORMAL_FONT = ESC + '\x21\x00\x00'

CONDENSED_MODE = ESC + SI + '\x00'
NORMAL_MODE = DC2

CENTRALIZE = ESC + 'j\x01'
DESCENTRALIZE = ESC + 'j\x00'

DOUBLE_HEIGHT_ON = ESC + 'w\x01'
DOUBLE_HEIGHT_OFF = ESC + 'w\x00'

SET_BOLD = ESC + 'E'
UNSET_BOLD = ESC + 'F'


@implementer(INonFiscalPrinter)
class DR700(SerialBase):

    supported = True
    model_name = "Daruma DR 700"

    max_characters = 57

    def __init__(self, port, consts=None):
        SerialBase.__init__(self, port)
        self.set_condensed()
        self.descentralize()
        self.unset_bold()
        self.unset_double_height()

    def centralize(self):
        self.write(CENTRALIZE)

    def descentralize(self):
        self.write(DESCENTRALIZE)

    def set_bold(self):
        self.write(SET_BOLD)

    def unset_bold(self):
        self.write(UNSET_BOLD)

    def set_condensed(self):
        self.write(CONDENSED_MODE)

    def unset_condensed(self):
        self.write(NORMAL_MODE)

    def set_double_height(self):
        self.write(DOUBLE_HEIGHT_ON)

    def unset_double_height(self):
        self.write(DOUBLE_HEIGHT_OFF)

    def print_line(self, data):
        self.write(data + b'\n')

    def print_inline(self, data):
        self.write(data)

    def print_barcode(self, code):
        code_128 = chr(5)
        width = chr(2)
        height = chr(80)
        barcode_label = chr(0)
        self.write(ESC + '\x62%s%s%s%s%s\x00' % (code_128, width, height,
                                                 barcode_label, code))
        self.write('\x0A')

    def print_qrcode(self, code):
        bytes_len = len(code)
        min_size = chr(bytes_len >> 8)
        max_size = chr((bytes_len & 255) + 2)
        width = chr(3)
        # Correction level: auto
        correction = chr(0)
        self.write(ESC + '\x81%s%s%s%s%s' % (max_size, min_size, width, correction, code))
        self.write('\x0A')

    def cut_paper(self):
        # FIXME: Ensure the paper is safely out of the paper-cutter before
        #        executing the cut.
        self.print_inline('\n' * 2)
        self.write(ESC + '\x6d')
