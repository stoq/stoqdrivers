# -*- Mode: Python; coding: iso-8859-1 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Stoqdrivers
## Copyright (C) 2012 Async Open Source <http://www.async.com.br>
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
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
## USA.
##
## Author(s): Stoq Team <stoq-devel@async.com.br>
##
"""
Epson FBIII ECF driver
"""
from decimal import Decimal

from stoqdrivers.printers.epson.FBII import FBII

# Coupons status
CLOSED_COUPON = '0000'
OPENED_FISCAL_COUPON = '0001'
OPENED_NON_FISCAL_COUPON = '1000'


class FBIII(FBII):
    model_name = "Epson FBIII"

    def apply_discount(self, id, discount):
        value = int(discount * Decimal('1e2'))
        self._send_command('0A07', '0010', id, str(value))

    def apply_markup(self, id, markup):
        value = int(markup * Decimal('1e2'))
        self._send_command('0A07', '0011', id, str(value))
