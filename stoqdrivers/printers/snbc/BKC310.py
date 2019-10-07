# -*- Mode: Python; coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Stoqdrivers
## Copyright (C) 2019 Stoq Tecnologia <http://stoq.link>
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
import qrcode

from zope.interface import implementer

from stoqdrivers.utils import GRAPHICS_24BITS
from stoqdrivers.usbbase import UsbBase
from stoqdrivers.escpos import EscPosMixin
from stoqdrivers.interfaces import INonFiscalPrinter


@implementer(INonFiscalPrinter)
class BKC310(UsbBase, EscPosMixin):
    out_ep = 0x02
    cut_line_feeds = 0

    supported = True
    model_name = "SNBC BK-C310"

    def print_qrcode(self, code):
        qr = qrcode.QRCode(version=1, border=4)
        qr.add_data(code)
        self.print_matrix(qr.get_matrix(), GRAPHICS_24BITS, multiplier=3)
