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

LINE_FEED = '\x1bA\x00'
CENTRALIZE = '\x1ba\x01'
DESCENTRALIZE = '\x1ba\x00'
CONDENSED_MODE = '\x1bSI'
NORMAL_MODE = '\x1bH'
SET_BOLD = '\x1bE'
UNSET_BOLD = '\x1bF'
BARCODE_128 = '\x1Dkn'

_GRAPHICS_8BITS = 8
_GRAPHICS_24BITS = 24
_GRAPHICS_MAX_COLS = {
    _GRAPHICS_8BITS: 576,
    _GRAPHICS_24BITS: 1728,
}
_GRAPHICS_CMD = {
    _GRAPHICS_8BITS: '\x1b\x4b%s%s%s',
    _GRAPHICS_24BITS: '\x1b\x2a\x21%s%s%s',
}


def _bits2byte(bits):
    return sum(2 ** i if bit else 0 for i, bit in enumerate(reversed(bits)))


def _matrix2graphics(graphics_api, matrix, multiplier=1, centralized=True):
    if not graphics_api in [_GRAPHICS_8BITS, _GRAPHICS_24BITS]:
        raise ValueError("Graphics api %s not supported" % (graphics_api, ))

    sub_len = graphics_api / multiplier

    for i in xrange(0, len(matrix), sub_len):
        bytes_ = []
        sub = matrix[i:i + sub_len]
        if len(sub) < sub_len:
            sub.extend([[False] * len(matrix)] * (sub_len - len(sub)))

        for j in xrange(len(matrix)):
            bits = []
            for bit in sub:
                bits.extend([bit[j]] * multiplier)

            if graphics_api == _GRAPHICS_8BITS:
                # The 3 is to compensate for the fact that each pixel is
                # 3x larger vertically than horizontally
                bytes_.extend([_bits2byte(bits)] * 3 * multiplier)
            elif graphics_api == _GRAPHICS_24BITS:
                splitted_bytes = []
                for k in xrange(0, 24, 8):
                    splitted_bytes.append(_bits2byte(bits[k: k + 8]))
                bytes_.extend(splitted_bytes * multiplier)
            else:
                raise AssertionError

        if centralized:
            diff = _GRAPHICS_MAX_COLS[graphics_api] - len(bytes_)
            if diff:
                bytes_ = ([0] * (diff / 2)) + bytes_

        divide_len_by = graphics_api / 8
        yield ''.join(chr(b) for b in bytes_), len(bytes_) / divide_len_by


class MP2100TH(SerialBase):
    implements(INonFiscalPrinter)

    supported = True
    model_name = "Bematech MP2100 TH"

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
        self.write('\x1d\x68%s' % chr(120))
        # Normal width
        self.write('\x1d\x77\x02')
        # No HRI (human readable information)
        self.write('\x1d\x48\x00')

        cmd = '\x1d\x6b\x49%s%s' % (chr(len(code)), code)
        self.write(cmd)

    def print_qrcode(self, code):
        qr = qrcode.QRCode(version=1, border=4)
        qr.add_data(code)
        self.write('\x00')
        self._print_matrix(_GRAPHICS_8BITS, qr.get_matrix())

    #
    #  Private
    #

    def _print_matrix(self, graphics_api, matrix, multiplier=1):
        for line, line_len in _matrix2graphics(graphics_api, matrix, multiplier):
            assert line_len <= _GRAPHICS_MAX_COLS[graphics_api]
            n2 = 0
            n1 = line_len
            # line_len = n1 + n2 * 256
            while n1 >= 256:
                n2 += 1
                n1 -= 256

            self.write(_GRAPHICS_CMD[graphics_api] % (chr(n1), chr(n2), line))
            self.write(LINE_FEED)
