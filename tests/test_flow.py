# -*- Mode: Python; coding: iso-8859-1 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Stoqdrivers
## Copyright (C) 2005 Async Open Source <http://www.async.com.br>
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
## Author(s):   Henrique Romano        <henrique@async.com.br>
##
"""
stoqdrivers/tests/test_flow.py:

    A simple test case to check if the coupon workflow is managed
    properly.
"""

from stoqdrivers.constants import UNIT_EMPTY, TAX_NONE, MONEY_PM
from stoqdrivers.devices.printers.fiscal import FiscalPrinter
from stoqdrivers.exceptions import (CouponOpenError, CancelItemError,
                                    CloseCouponError, PaymentAdditionError,
                                    ItemAdditionError, PendingReduceZ,
                                    PendingReadX)

def test():
    printer = FiscalPrinter()

    # Test 01 - Try add an item with the coupon cancelled
    try:
        printer.open("Henrique", "XXX", "666")
        printer.cancel()
        printer.add_item("0001", 2, 1.30, UNIT_EMPTY, "Cigarro",
                         TAX_NONE, 0, 0)
    except CouponOpenError:
        print "Test 1: OK."
    except PendingReadX:
        printer.summarize()
        return
    except PendingReduceZ:
        printer.close_till()
        return

    # Test 02 - Try cancel an item already cancelled
    printer.open("Henrique", "XXX", "666")
    item_1 = printer.add_item("0001", 2, 1.30, UNIT_EMPTY,
                              "Cigarro", TAX_NONE, 0, 0)
    item_2 = printer.add_item("0002", 3, 5.20, UNIT_EMPTY,
                              "Cerveja", TAX_NONE, 0, 0)
    item_3 = printer.add_item("0003", 1, 2.30, UNIT_EMPTY,
                              "Isqueiro", TAX_NONE, 0, 0)
    try:
        printer.cancel_item(item_3)
        printer.cancel_item(item_3)
    except CancelItemError:
        print "Test 2: OK."

    # Test 03 - Try close the coupon without totalize it
    try:
        printer.close()
    except CloseCouponError:
        print "Test 3: OK."

    # Test 04 - Try add a payment without totalize the coupon
    try:
        printer.add_payment(MONEY_PM, 100.00, "")
    except PaymentAdditionError:
        print "Test 4: OK."

    # Test 05 - Try add an item with the coupon totalized
    printer.totalize(0, 0, TAX_NONE)
    try:
        printer.add_item("0005", 4, 2.30, UNIT_EMPTY,
                         "Cigarro", TAX_NONE, 0, 0)
    except ItemAdditionError:
        print "Test 5: OK."

    # Test 06 - Try close the with no payments
    try:
        printer.close()
    except CloseCouponError:
        print "Test 6: OK."

    printer.add_payment(MONEY_PM, 100.00, "")
    printer.close()

if __name__ == "__main__":
    test()