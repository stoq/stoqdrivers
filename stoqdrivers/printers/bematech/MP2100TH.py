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

CENTRALIZE = '\x1ba\x01'
DESCENTRALIZE = '\x1ba\x00'
CONDENSED_MODE = '\x1bSI'
NORMAL_MODE = '\x1bH'
SET_BOLD = '\x1bE'
UNSET_BOLD = '\x1bF'
BARCODE_128 = '\x1Dkn'


class MP2100TH(SerialBase):
    implements(INonFiscalPrinter)

    def __init__(self, port, consts=None):
        self._is_bold = False
        self._is_centralized = False
        SerialBase.__init__(self, port)
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
        # Change the height
        self.write('\x1d\x68%s' % chr(120))
        # Normal width
        self.write('\x1d\x77\x02')
        # No HRI (human readable information)
        self.write('\x1d\x48\x00')

        cmd = '\x1d\x6b\x49%s%s' % (chr(len(code)), code)
        self.write(cmd)
