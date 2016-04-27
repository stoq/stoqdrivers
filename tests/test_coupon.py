# -*- Mode: Python; coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Stoqdrivers
## Copyright (C) 2006-2007 Async Open Source <http://www.async.com.br>
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
##              Johan Dahlin           <jdahlin@async.com.br>
##

import datetime
from decimal import Decimal
import os
import unittest

from zope.interface import implements


import stoqdrivers
from stoqdrivers.enum import TaxType, UnitType
from stoqdrivers.exceptions import (CouponOpenError,
                                    PendingReadX, PaymentAdditionError,
                                    AlreadyTotalized, CancelItemError,
                                    InvalidValue, CloseCouponError,
                                    CouponNotOpenError)
from stoqdrivers.interfaces import ISerialPort
from stoqdrivers.printers.fiscal import FiscalPrinter
from stoqdrivers.serialbase import SerialPort


# The directory where tests data will be stored
RECORDER_DATA_DIR = "data"


class LogSerialPort:
    """ A decorator for the SerialPort object expected by the driver to test,
    responsible for log all the bytes read/written.
    """
    implements(ISerialPort)

    def __init__(self, port):
        self._port = port
        self._bytes = []
        self._last = None
        self._buffer = ''

    def setDTR(self):
        return self._port.setDTR()

    def getDSR(self):
        return self._port.getDSR()

    @property
    def parity(self):
        return self._port.parity

    @parity.setter
    def parity(self, value):
        self._port.parity = value

    @property
    def timeout(self):
        return self._port.timeout

    @timeout.setter
    def timeout(self, value):
        self._port.timeout = value

    @property
    def writeTimeout(self):
        return self._port.writeTimeout

    @writeTimeout.setter
    def writeTimeout(self, value):
        self._port.writeTimeout = value

    def read(self, n_bytes=1):
        data = self._port.read(n_bytes)
        self._buffer += data
        self._last = 'R'
        return data

    def write(self, bytes):
        if self._last == 'R':
            self._bytes.append(('R', self._buffer))
            self._buffer = ''

        self._bytes.append(('W', bytes))
        self._port.write(bytes)
        self._last = 'W'

    def save(self, filename):
        if self._buffer:
            self._bytes.append(('R', self._buffer))
        fd = open(filename, "w")
        for type, line in self._bytes:
            fd.write("%s %s\n" % (type, repr(line)[1:-1]))
        fd.close()


class PlaybackPort:
    implements(ISerialPort)

    def __init__(self, datafile):
        self._input = []
        self._output = ''
        self._load_data(datafile)

    def setDTR(self):
        pass

    def getDSR(self):
        return True

    def write(self, bytes):
        n_bytes = len(bytes)
        data = "".join([self._input.pop(0) for i in xrange(n_bytes)])
        if bytes != data:
            raise ValueError("Written data differs from the expected:\n"
                             "WROTE:    %r\n"
                             "RECORDED: %r\n" % (data, bytes))

    def read(self, n_bytes=1):
        data = self._output[:n_bytes]
        if not data:
            return None
        self._output = self._output[n_bytes:]
        return data

    def _convert_data(self, data):
        data = data.replace('\\n', '\n')
        data = data.replace('\\r', '\r')
        data = data.replace('\\t', '\t')
        data = data.replace('\\\\', '\\')
        data = data.split('\\x')
        if len(data) == 1:
            data = data[0]
        else:
            n = ''
            for p in data:
                if len(p) <= 1:
                    n += p
                else:
                    try:
                        data = p[:2].decode('hex')
                    except:
                        data = p[:2]
                    n += data + p[2:]
            data = n
        return data

    def _load_data(self, datafile):
        fd = open(datafile, "r")
        for n, line in enumerate(fd.readlines()):
            data = self._convert_data(line[2:-1])

            if line.startswith("W"):
                self._input.extend(data)
            elif line.startswith("R"):
                self._output += data
            else:
                raise TypeError("Unrecognized entry type at %s:%d: %r"
                                % (datafile, n + 1, line[0]))
        fd.close()


class _BaseTest(unittest.TestCase):
    def __init__(self, test_name):
        self._test_name = test_name
        unittest.TestCase.__init__(self, test_name)

    def tearDown(self):
        filename = self._get_recorder_filename()
        if not os.path.exists(filename):
            self._port.save(filename)

    def setUp(self):
        filename = self._get_recorder_filename()
        if not os.path.exists(filename):
            # Change this path to the serial port and set the baudrate used by
            # fiscal printer when recreating the tests.
            real_port = SerialPort('/tmp/stoq-ecf', baudrate=9600)
            self._port = LogSerialPort(real_port)
        else:
            self._port = PlaybackPort(filename)

        self._device = self.device_class(brand=self.brand,
                                         model=self.model,
                                         port=self._port)
        payments = self._device.get_payment_constants()
        assert len(payments) >= 1
        self._payment_method = payments[0][0]
        self._taxnone = self._device.get_tax_constant(TaxType.NONE)

    def _get_recorder_filename(self):
        testdir = os.path.join(os.path.dirname(stoqdrivers.__file__),
                               "..", "tests")
        test_name = self._test_name
        if test_name.startswith('test_'):
            test_name = test_name[5:]
        test_name = test_name.replace('_', '-')

        filename = "%s-%s-%s.txt" % (self.brand, self.model, test_name)
        return os.path.join(testdir, RECORDER_DATA_DIR, filename)


class _TestCoupon(object):
    """ Test a coupon creation """
    device_class = FiscalPrinter

    #
    # Helper methods
    #

    def _open_coupon(self):
        self._device.identify_customer("Henrique Romano", "Async",
                                       "1234567890")
        while True:
            try:
                self._device.open()
                break
            except CouponOpenError:
                self._device.cancel()
            except PendingReadX:
                self._device.summarize()

    #
    # Tests
    #

    def test_add_item(self):
        self._open_coupon()
        # 1. Specify discount and surcharge at the same time
        self.failUnlessRaises(TypeError, self._device.add_item, u"123456",
                              u"Monitor LG Flatron T910B", Decimal("500"),
                              self._taxnone, discount=Decimal("1"),
                              surcharge=Decimal("1"))

        # 2. Specify unit_desc with unit different from UnitType.CUSTOM
        self.failUnlessRaises(ValueError, self._device.add_item, u"123456",
                              u"Monitor LG Flatron T910B", Decimal("500"),
                              self._taxnone, unit=UnitType.LITERS,
                              unit_desc="XX")

        # 3. Specify unit as UnitType.CUSTOM and not supply a unit_desc
        self.failUnlessRaises(ValueError, self._device.add_item, u"123456",
                              u"Monitor LG Flatron T910B", Decimal("500"),
                              self._taxnone, unit=UnitType.CUSTOM)

        # 4. Specify unit as UnitType.CUSTOM and unit_desc greater than 2 chars
        self.failUnlessRaises(ValueError, self._device.add_item, u"123456",
                              u"Monitor LG Flatron T910B", Decimal("500"),
                              self._taxnone, unit=UnitType.CUSTOM,
                              unit_desc="XXXX")

        # 5. Add item without price
        self.failUnlessRaises(InvalidValue, self._device.add_item, u"123456",
                              u"Monitor LG Flatron T910B", Decimal("0"),
                              self._taxnone)

        #
        # 6. Dataregis specific: the first 6 chars of the product code must
        # be digits.
        self._device.add_item(u"ABCDEF", u"Monitor LG 775N", Decimal("10"),
                              self._taxnone, items_quantity=Decimal("2"))

        # A "normal" item...
        self._device.add_item(u"987654", u"Monitor LG 775N", Decimal("10"),
                              self._taxnone, items_quantity=Decimal("1"))

        # A item with customized unit
        self._device.add_item(u"123456", u"Monitor LG 775N", Decimal("10"),
                              self._taxnone, items_quantity=Decimal("1"),
                              unit=UnitType.CUSTOM, unit_desc="Tx")

        # A item with surcharge
        self._device.add_item(u"123456", u"Monitor LG 775N", Decimal("10"),
                              self._taxnone, items_quantity=Decimal("1"),
                              surcharge=Decimal("1"))

        # 7. Add item with coupon totalized
        self._device.totalize()
        self.failUnlessRaises(AlreadyTotalized,
                              self._device.add_item, u"123456", u"Monitor LG Flatron T910B",
                              Decimal("10"), self._taxnone)

        self._device.add_payment(self._payment_method, Decimal("100"))
        self._device.close()

        # 8. Add item without coupon
        if self.brand != 'bematech':
            self.failUnlessRaises(CouponNotOpenError, self._device.add_item,
                                  u"123456", u"Monitor LG Flatron T910B",
                                  Decimal("500"), self._taxnone,
                                  discount=Decimal("1"))

    def test_cancel_item(self):
        self._open_coupon()
        item_id = self._device.add_item(u"987654", u"Monitor LG 775N",
                                        Decimal("10"), self._taxnone,
                                        items_quantity=Decimal("1"))
        # 1. Cancel invalid item
        self.failUnlessRaises(CancelItemError,
                              self._device.cancel_item, item_id + 9)
        self._device.cancel_item(item_id)
        # 2. Cancel item twice
        self.failUnlessRaises(CancelItemError,
                              self._device.cancel_item, item_id)
        item_id = self._device.add_item(u"987654", u"Monitor LG 775N",
                                        Decimal("10"), self._taxnone,
                                        items_quantity=Decimal("1"))
        self._device.totalize()
        self._device.add_payment(self._payment_method, Decimal("100"))
        self._device.close()

    def test_totalize(self):
        self._open_coupon()
        self._device.add_item(u"987654", u"Monitor LG 775N", Decimal("10"),
                              self._taxnone, items_quantity=Decimal("1"))
        # 1. discount and surcharge together
        self.failUnlessRaises(TypeError, self._device.totalize,
                              Decimal("1"), Decimal("1"))

        # 2. specify surcharge with taxcode equals TaxType.NONE
        self.failUnlessRaises(ValueError, self._device.totalize,
                              surcharge=Decimal("1"), taxcode=TaxType.NONE)

        # 3. surcharge with taxcode equals to TaxType.ICMS
        coupon_total = self._device.totalize(surcharge=Decimal("1"),
                                             taxcode=TaxType.ICMS)
        self.assertEquals(coupon_total, Decimal("11.00"))
        self._device.add_payment(self._payment_method, Decimal("12"))
        self._device.close()

    def test_add_payment(self):
        self._open_coupon()
        self._device.add_item(u"987654", u"Monitor LG 775N", Decimal("10"),
                              self._taxnone)
        # Add payment without totalize the coupon
        self.failUnlessRaises(PaymentAdditionError,
                              self._device.add_payment,
                              self._payment_method,
                              Decimal("100"))
        self._device.totalize()

        self._device.add_payment(self._payment_method, Decimal("100"))
        self._device.close()

    def test_close_coupon(self):
        self._open_coupon()
        self._device.add_item(u"987654", u"Monitor LG 775N", Decimal("10"),
                              self._taxnone)
        # 1. Close without totalize
        self.failUnlessRaises(CloseCouponError, self._device.close)

        # 2. Close without payments
        self._device.totalize()
        self.failUnlessRaises(CloseCouponError, self._device.close)

        # 3. Close with the payments total value lesser than the totalized
        self._device.add_payment(self._payment_method, Decimal("5"))
        self.failUnlessRaises(CloseCouponError, self._device.close)

        self._device.add_payment(self._payment_method, Decimal("100"))
        # 4. Close the coupon with a BIG message
        self._device.close(u"ÃãÁáÀàÂâÉéÊêÍíÕõÓóÔôÚúÇç!@#$%^&*ªº\n"
                           "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789\n"
                           "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
                           "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
                           "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
                           "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")

    def test_cancel_coupon(self):
        self._open_coupon()
        self._device.add_item(u"987654", u"Monitor LG 775N", Decimal("10"),
                              self._taxnone)
        self._device.cancel()

    def test_till_add_cash(self):
        self._device.till_add_cash(Decimal("10"))

    def test_till_remove_cash(self):
        self._device.till_remove_cash(Decimal("10"))

    def test_coupon_open(self):
        self._open_coupon()
        # Bematech does not have an easy way to check if a coupon is
        # already opened
        if self.brand != 'bematech':
            self.failUnlessRaises(CouponOpenError, self._device.open)
        self._device.cancel()

    def _get_constant(self, constants, value):
        for device_value, name in constants:
            if name.lower() == value.lower():
                return device_value

        return None

    def get_card_constant(self):
        return self._get_constant(self._device.get_payment_constants(),
                                  u'Cartao Credito')

    def get_card_payment_receipt(self):
        return self._device.get_payment_receipt_identifier(u'Cartao Credito')

    def test_payment_receipt(self):
        payment_id = self.get_card_constant()
        receipt_id = self.get_card_payment_receipt()

        self._open_coupon()
        self._device.add_item(u"987654", u"Monitor LG 775N", Decimal(10),
                              self._taxnone)

        self._device.totalize()
        self._device.add_payment(payment_id, Decimal(10))
        coo = self._device.close()

        self._device.payment_receipt_open(receipt_id, coo, payment_id,
                                          Decimal(10))
        self._device.payment_receipt_print('Stoq payment receipt')
        self._device.payment_receipt_close()

    def test_summarize(self):
        self._device.summarize()

    def test_has_open_coupon(self):
        self._open_coupon()
        has_open_coupon = self._device.has_open_coupon()
        self.assertEquals(has_open_coupon, True)
        self._device.cancel()
        has_open_coupon = self._device.has_open_coupon()
        self.assertEquals(has_open_coupon, False)

    def test_cancel_last_coupon(self):
        # Cancel non fiscal coupon.
        # Bematech MP20 does not support this
        if self.model != 'MP20':
            self._device.till_add_cash(Decimal("10"))
            self._device.cancel_last_coupon()

        # Cancel fiscal coupon.
        self._open_coupon()
        self._device.add_item(u"987654", u"Monitor LG 775N", Decimal("10"),
                              self._taxnone, items_quantity=Decimal("1"))
        self._device.totalize()
        self._device.add_payment(self._payment_method, Decimal("100"))
        self._device.close()
        self._device.cancel_last_coupon()

    def test_gerencial_report(self):
        self._device.gerencial_report_open()
        # Send a big report to test the line breaks and limit of columns number
        self._device.gerencial_report_print("Teste Relatorio Gerencial\n"
                                            "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789\n\n"
                                            "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789\n\n"
                                            "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789\n\n"
                                            "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789\n\n"
                                            "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789\n\n"
                                            "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789\n"
                                            "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789\n"
                                            "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
                                            "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
        self._device.gerencial_report_close()

    def test_read_memory(self):
        start = datetime.date(year=2013, month=01, day=01)
        end = datetime.date(year=2013, month=01, day=30)
        self._device.till_read_memory(start, end)

    def test_read_memory_by_reductions(self):
        self._device.till_read_memory_by_reductions(start=1, end=10)

    def test_sintegra(self):
        self._device.get_sintegra()


class DarumaFS345(_TestCoupon, _BaseTest):
    brand = 'daruma'
    model = 'FS345'


class DarumaFS2100(_TestCoupon, _BaseTest):
    brand = 'daruma'
    model = 'FS2100'

    # Overwrite methods to use accentuation in payment method name.
    # The fiscal printer used in tests has the payment constants,
    # registered with accentuation.
    def get_card_constant(self):
        return self._get_constant(self._device.get_payment_constants(),
                                  u"Cartão Crédito")

    def get_card_payment_receipt(self):
        return self._device.get_payment_receipt_identifier(u"Cartão Crédito")


# XXX: This tests wore not done with a real printer, we used an emulator
class BematechMP20(_TestCoupon, _BaseTest):
    brand = 'bematech'
    model = 'MP20'


class BematechMP25FI(_TestCoupon, _BaseTest):
    brand = 'bematech'
    model = 'MP25'


# XXX: This tests wore not done with a real printer, we used an emulator
class BematechMP2100(_TestCoupon, _BaseTest):
    brand = 'bematech'
    model = 'MP2100'


class FiscNet(_TestCoupon, _BaseTest):
    brand = "fiscnet"
    model = "FiscNetECF"

    def get_card_constant(self):
        return self._get_constant(self._device.get_payment_constants(),
                                  u'Cartão Crédito')

    def get_card_payment_receipt(self):
        # this driver does not need one.
        return None


class EpsonFBIII(_TestCoupon, _BaseTest):
    brand = "epson"
    model = "FBIII"


# class DataregisEP375(_TestCoupon, _BaseTest):
#     brand = "dataregis"
#     model = "EP375"
