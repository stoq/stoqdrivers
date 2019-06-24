# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2016-2019 Stoq Tecnologia <http://stoq.com.br>
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
from stoqdrivers.escpos import EscPosMixin, ESC, GS
from stoqdrivers.interfaces import INonFiscalPrinter
from stoqdrivers.serialbase import SerialBase


@implementer(INonFiscalPrinter)
class I9(SerialBase, EscPosMixin):
    DOUBLE_HEIGHT_ON = GS + '!' + '\x01'
    DOUBLE_HEIGHT_OFF = GS + '!' + '\x00'

    cut_line_feeds = 3
    supported = True
    model_name = "Elgin I9"

    def __init__(self, port, consts=None):
        SerialBase.__init__(self, port)
        EscPosMixin.__init__(self)

    def open_drawer(self):
        m = '0'
        t1 = '0'
        t2 = '5'  # number of milliseconds to activate the electrical signal.
        self.write(ESC + 'p' + m + t1 + t2)

    def is_drawer_open(self):
        self.write(GS + 'r2')
        data = ord(self.read(1)[0])
        if self.inverted_drawer:
            return data != 0
        else:
            return data == 0
