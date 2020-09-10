# -*- Mode: Python; coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

#
# Stoqdrivers
# Copyright (C) 2005-2007 Async Open Source <http://www.async.com.br>
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
# Author(s):   Johan Dahlin     <jdahlin@async.com.br>
#              Henrique Romano  <henrique@async.com.br>
#

from collections import namedtuple
import datetime
from decimal import Decimal
import logging
from numbers import Real
import traceback
import sys

from stoqdrivers.exceptions import (CloseCouponError, PaymentAdditionError,
                                    AlreadyTotalized, InvalidValue)
from stoqdrivers.enum import TaxType, UnitType
from stoqdrivers.printers.base import BasePrinter
from stoqdrivers.utils import encode_text
from stoqdrivers.translation import stoqdrivers_gettext

_ = stoqdrivers_gettext

log = logging.getLogger('stoqdrivers.fiscalprinter')

#
# FiscalPrinter interface
#


class FiscalPrinter(BasePrinter):
    def __init__(self, brand=None, model=None, device=None, config_file=None,
                 *args, **kwargs):
        BasePrinter.__init__(self, brand, model, device, config_file, *args,
                             **kwargs)
        self._has_been_totalized = False
        self.payments_total_value = Decimal("0.0")
        self.totalized_value = Decimal("0.0")
        self._capabilities = self._driver.get_capabilities()
        self._charset = self._driver.coupon_printer_charset
        try:
            self.setup()
            self._setup_complete = True
        except Exception:
            log.error(''.join(traceback.format_exception(*sys.exc_info())))
            self._setup_complete = False

    def setup_complete(self):
        return self._setup_complete

    def get_capabilities(self):
        return self._capabilities

    def _format_text(self, text):
        return encode_text(text, self._charset)

    def setup(self):
        log.info('setup()')
        self._driver.setup()

    def identify_customer(self, customer_name: str, customer_address: str, customer_id: str):
        log.info('identify_customer(customer_name=%r, '
                 'customer_address=%r, customer_id=%r)' % (
                     customer_name, customer_address, customer_id))

        self._driver.coupon_identify_customer(
            self._format_text(customer_name),
            self._format_text(customer_address),
            self._format_text(customer_id))

    def coupon_is_customer_identified(self):
        return self._driver.coupon_is_customer_identified()

    def has_open_coupon(self):
        log.info('has_open_coupon()')
        return self._driver.has_open_coupon()

    def open(self):
        log.info('coupon_open()')

        return self._driver.coupon_open()

    def add_item(self, item_code: str, item_description: str, item_price: Real, taxcode: TaxType,
                 items_quantity=Decimal("1.0"), unit=UnitType.EMPTY,
                 discount=Decimal("0.0"), surcharge=Decimal("0.0"),
                 unit_desc=""):
        log.info("add_item(code=%r, description=%r, price=%r, "
                 "taxcode=%r, quantity=%r, unit=%r, discount=%r, "
                 "surcharge=%r, unit_desc=%r)" % (
                     item_code, item_description, item_price, taxcode,
                     items_quantity, unit, discount, surcharge, unit_desc))

        if self._has_been_totalized:
            raise AlreadyTotalized("the coupon is already totalized, you "
                                   "can't add more items")
        if discount and surcharge:
            raise TypeError("discount and surcharge can not be used together")
        elif unit != UnitType.CUSTOM and unit_desc:
            raise ValueError("You can't specify the unit description if "
                             "you aren't using UnitType.CUSTOM constant.")
        elif unit == UnitType.CUSTOM and not unit_desc:
            raise ValueError("You must specify the unit description when "
                             "using UnitType.CUSTOM constant.")
        elif unit == UnitType.CUSTOM and len(unit_desc) != 2:
            raise ValueError("unit description must be 2-byte sized string")
        if not item_price:
            raise InvalidValue("The item value must be greater than zero")

        if surcharge < 0:
            raise ValueError('Surcharge cannot be negative')
        if discount < 0:
            raise ValueError('Discount cannot be negative')

        return self._driver.coupon_add_item(
            self._format_text(item_code), self._format_text(item_description),
            item_price, taxcode, items_quantity, unit, discount, surcharge,
            unit_desc=self._format_text(unit_desc))

    def totalize(self, discount=Decimal(0), surcharge=Decimal(0),
                 taxcode=TaxType.NONE):
        log.info('totalize(discount=%r, surcharge=%r, taxcode=%r)' % (
            discount, surcharge, taxcode))

        if discount and surcharge:
            raise TypeError("discount and surcharge can not be used together")
        if surcharge and taxcode == TaxType.NONE:
            raise ValueError("to specify a surcharge you need specify its "
                             "tax code")
        result = self._driver.coupon_totalize(discount, surcharge, taxcode)
        self._has_been_totalized = True
        self.totalized_value = result
        return result

    def add_payment(self, payment_method: str, payment_value: Decimal, description=''):
        log.info("add_payment(method=%r, value=%r, description=%r)" % (
            payment_method, payment_value, description))

        if not self._has_been_totalized:
            raise PaymentAdditionError(_("You must totalize the coupon "
                                         "before add payments."))
        result = self._driver.coupon_add_payment(
            payment_method, payment_value,
            self._format_text(description))
        self.payments_total_value += payment_value
        return result

    def cancel(self):
        log.info('coupon_cancel()')
        retval = self._driver.coupon_cancel()
        self._has_been_totalized = False
        self.payments_total_value = Decimal("0.0")
        self.totalized_value = Decimal("0.0")
        return retval

    def cancel_last_coupon(self):
        """Cancel the last non fiscal coupon or the last sale."""
        log.info('cancel_last_coupon()')
        self._driver.cancel_last_coupon()

    def cancel_item(self, item_id: int):
        log.info('coupon_cancel_item(item_id=%r)' % (item_id,))

        return self._driver.coupon_cancel_item(item_id)

    def close(self, promotional_message=''):
        log.info('coupon_close(promotional_message=%r)' % (
            promotional_message))

        if not self._has_been_totalized:
            raise CloseCouponError(_("You must totalize the coupon before "
                                     "closing it"))
        if not self.payments_total_value:
            raise CloseCouponError(_("It is not possible close the coupon "
                                     "since there are no payments defined."))
        if self.totalized_value > self.payments_total_value:
            raise CloseCouponError(_("Isn't possible close the coupon since "
                                     "the payments total (%.2f) doesn't "
                                     "match the totalized value (%.2f).")
                                   % (self.payments_total_value,
                                      self.totalized_value))
        res = self._driver.coupon_close(
            self._format_text(promotional_message))
        self._has_been_totalized = False
        self.payments_total_value = Decimal("0.0")
        self.totalized_value = Decimal("0.0")
        return res

    def summarize(self):
        log.info('summarize()')

        return self._driver.summarize()

    def has_pending_reduce(self):
        pending = self._driver.has_pending_reduce()
        log.info('has_pending_reduce() = %s' % pending)
        return pending

    def open_till(self):
        log.info('open_till()')
        return self._driver.open_till()

    def close_till(self, previous_day=False):
        log.info('close_till(previous_day=%r)' % (previous_day,))

        return self._driver.close_till(previous_day)

    def till_add_cash(self, add_cash_value: Decimal):
        log.info('till_add_cash(add_cash_value=%r)' % (add_cash_value,))

        return self._driver.till_add_cash(add_cash_value)

    def till_remove_cash(self, remove_cash_value: Decimal):
        log.info('till_remove_cash(remove_cash_value=%r)' % (
            remove_cash_value,))

        return self._driver.till_remove_cash(remove_cash_value)

    def till_read_memory(self, start: datetime.date, end: datetime.date):
        assert start <= end <= datetime.date.today(), (
            "start must be less then end and both must be less today")
        log.info('till_read_memory(start=%r, end=%r)' % (
            start, end))

        return self._driver.till_read_memory(start, end)

    def till_read_memory_to_serial(self, start: datetime.date, end: datetime.date):
        assert start <= end <= datetime.date.today(), (
            "start must be less then end and both must be less today")
        log.info('till_read_memory(start=%r, end=%r)' % (
            start, end))

        return self._driver.till_read_memory_to_serial(start, end)

    def till_read_memory_by_reductions(self, start: int, end: int):
        assert end >= start > 0, ("start must be less then end "
                                  "and both must be positive")
        log.info('till_read_memory_by_reductions(start=%r, end=%r)' % (
            start, end))

        self._driver.till_read_memory_by_reductions(start, end)

    def gerencial_report_open(self):
        log.info('gerencial_report_open')
        return self._driver.gerencial_report_open()

    def gerencial_report_print(self, text):
        log.info('gerencial_report_print(text=%s)' % text)
        return self._driver.gerencial_report_print(text)

    def gerencial_report_close(self):
        log.info('gerencial_report_close')
        return self._driver.gerencial_report_close()

    def payment_receipt_open(self, identifier, coo, method, value):
        log.info('payment_receipt_open(identifier=%s, coo=%s, method=%s, value=%s)'
                 % (identifier, coo, method, value))
        return self._driver.payment_receipt_open(identifier, coo, method, value)

    def payment_receipt_print(self, text):
        log.info('payment_receipt_print(text=%s)' % text)
        return self._driver.payment_receipt_print(text)

    def payment_receipt_close(self):
        log.info('payment_receipt_close()')
        return self._driver.payment_receipt_close()

    def payment_receipt_print_duplicate(self):
        log.info('payment_receipt_print_duplicate()')
        return self._driver.payment_receipt_print_duplicate()

    def get_serial(self):
        log.info('get_serial()')

        return self._driver.get_serial()

    def query_status(self):
        log.info('query_status()')

        return self._driver.query_status()

    def status_reply_complete(self, reply):
        log.info('status_reply_complete(%s)' % (reply,))
        return self._driver.status_reply_complete(reply)

    def get_tax_constants(self):
        log.info('get_tax_constants()')

        return self._driver.get_tax_constants()

    def get_payment_constants(self):
        log.info('get_payment_constants()')

        return self._driver.get_payment_constants()

    def get_payment_receipt_identifier(self, method):
        log.info('get_payment_receipt_identifier(method=%s)' % method)
        return self._driver.get_payment_receipt_identifier(method)

    def get_ccf(self):
        """Fiscal Coupon Counter

        @returns: the last document ccf
        @rtype: integer
        """
        log.info('get_ccf()')

        return self._driver.get_ccf()

    def get_coo(self):
        """Operation Order Counter

        @returns: the last document coo
        @rtype: integer
        """
        log.info('get_coo()')

        return self._driver.get_coo()

    def get_gnf(self):
        """Nonfiscal Operation General Counter

        @returns: gnf
        @rtype: integer
        """
        log.info('get_gnf()')

        return self._driver.get_gnf()

    def get_crz(self):
        """Z Reduction Counter

        @returns: the last document crz
        @rtype: integer
        """
        log.info('get_crz()')

        return self._driver.get_crz()

    def get_sintegra(self):
        log.info('get_sintegra()')

        return self._driver.get_sintegra()

    @property
    def supports_duplicate_receipt(self):
        return self._driver.supports_duplicate_receipt

    @property
    def identify_customer_at_end(self):
        return self._driver.identify_customer_at_end


SintegraData = namedtuple("SintegraData", "opening_date serial serial_id coupon_start coupon_end "
                                          "crz cro coo period_total total taxes")
