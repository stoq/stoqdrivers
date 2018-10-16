# -*- Mode: Python; coding: iso-8859-1 -*-
# vi:si:et:sw=4:sts=4:ts=4
# Stoqdrivers
# Copyright (C) 2018 Async Open Source <http://www.async.com.br>
# All rights reserved
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
# USA.
#
from decimal import Decimal

from zope.interface import implementer

from stoqdrivers.exceptions import InvalidReply
from stoqdrivers.interfaces import IScale, IScaleInfo
from stoqdrivers.serialbase import SerialBase, SerialPort

STX = 0x02
ETX = 0x03

PRICE_PRECISION = 2
QUANTITY_PRECISION = 3


@implementer(IScaleInfo)
class Package:
    SIZE = 22

    def __init__(self, raw_data):
        self.code = None
        self.price_per_kg = None
        self.total_price = None
        self.weight = None
        self._parse(raw_data)

    def _parse(self, data):
        if not data:
            return
        elif ord(data[0]) != STX or len(data) != self.SIZE:
            raise InvalidReply("Received inconsistent data")

        self.weight = Decimal(data[1:7]) / (10 ** QUANTITY_PRECISION)
        self.price_per_kg = Decimal(data[8:14]) / (10 ** PRICE_PRECISION)
        self.total_price = Decimal(data[15:21]) / (10 ** PRICE_PRECISION)


@implementer(IScale)
class MicP15(SerialBase):
    CMD_PREFIX = "\x05"
    EOL_DELIMIT = chr(ETX)

    model_name = "Micheletti P15"

    def __init__(self, device, consts=None):
        SerialBase.__init__(self, device)
        self._package = None

    def _get_package(self):
        # PESO, PRECO, TOTAL
        # b'\x02  0800  99999  79999\x03'
        reply = self.writeline('')

        # The sum is just because readline (called internally by writeline)
        # remove the EOL_DELIMIT from the package received and we need send
        # to Package's constructor the whole data.
        return Package(reply + MicP15.EOL_DELIMIT)

    #
    # IScale implementation
    #

    def read_data(self):
        return self._get_package()


if __name__ == "__main__":
    port = SerialPort('/dev/ttyS0')
    r = MicP15(port)
    data = r.read_data()

    print("WEIGHT:", data.weight)
    print("PRICE BY KG:", data.price_per_kg)
    print("TOTAL PRICE:", data.total_price)
    print("CODE:", data.code)
