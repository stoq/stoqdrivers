# -*- Mode: Python; coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

#
# Stoqdrivers
# Copyright (C) 2005-2011 Async Open Source <http://www.async.com.br>
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
# Author(s):   Stoq Team  <stoq-devel@async.com.br>
#
"""
A simple implementation of a virtual printer.
"""

import datetime
from decimal import Decimal
import json
import os
from unittest import mock

try:
    from gi.repository import Gtk, Pango
except ImportError:
    Gtk = mock.Mock()
    Pango = mock.Mock()
from zope.interface import implementer

from stoqdrivers.enum import PaymentMethodType, TaxType, UnitType
from stoqdrivers.exceptions import (CouponTotalizeError, PaymentAdditionError,
                                    CloseCouponError, CouponOpenError,
                                    CancelItemError, ItemAdditionError,
                                    DriverError, PrinterOfflineError)
from stoqdrivers.interfaces import ICouponPrinter, INonFiscalPrinter
from stoqdrivers.printers.base import BaseDriverConstants
from stoqdrivers.printers.capabilities import Capability
from stoqdrivers.printers.fiscal import SintegraData
from stoqdrivers.translation import stoqdrivers_gettext

_ = stoqdrivers_gettext

# Global state of the printer. Even if we create multiple instances of the printer during runtime
# (which should not happen), all of them will share the same state.
_printer_off = False
_drawer_open = False


class CouponItem:
    def __init__(self, id, quantity, value):
        self.id, self.quantity, self.value = id, quantity, value

    def get_total_value(self):
        return self.quantity * self.value


class FakeConstants(BaseDriverConstants):
    _constants = {
        UnitType.WEIGHT: 'F',
        UnitType.METERS: 'G ',
        UnitType.LITERS: 'H',
        UnitType.EMPTY: 'I',
    }

    _payment_constants = {
        PaymentMethodType.MONEY: 'M',
        PaymentMethodType.CHECK: 'C',
        PaymentMethodType.BILL: 'B',
        PaymentMethodType.CREDIT_CARD: 'R',
        PaymentMethodType.DEBIT_CARD: 'D',
        PaymentMethodType.FINANCIAL: 'F',
        PaymentMethodType.GIFT_CERTIFICATE: 'G',
    }

    _payment_descriptions = {
        'M': 'Dinheiro',
        'C': 'Cheque',
        'B': 'Boleto',
        'R': u'Cartão Crédito',
        'D': u'Cartão Débito',
        'F': u'Financeira',
        'G': u'Vale Compras',
    }

    _tax_constants = [
        (TaxType.SUBSTITUTION, 'TS', None),
        (TaxType.EXEMPTION, 'TE', None),
        (TaxType.NONE, 'TN', None),
        (TaxType.CUSTOM, 'T1', Decimal(18)),
        (TaxType.CUSTOM, 'T2', Decimal(12)),
        (TaxType.CUSTOM, 'T3', Decimal(5)),
        (TaxType.SERVICE, 'S0', Decimal(3)),
    ]


class OutputWindow(Gtk.Window):
    _instance = None

    def __init__(self):
        self._printer = None
        Gtk.Window.__init__(self)
        self.set_title(_("ECF Emulator"))
        self.set_size_request(380, 320)
        self.move(0, 0)
        self.set_deletable(False)
        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self.vbox)

        self._create_ui()

    @classmethod
    def get_instance(cls):
        if cls._instance:
            return cls._instance
        cls._instance = cls()
        return cls._instance

    def set_printer(self, printer):
        self._printer = printer

    def _create_ui(self):
        sw = Gtk.ScrolledWindow()
        # FIXME: The overlay scrolling when a TextView is inside a
        # ScrolledWindow is somewhat broken in a way that it would make it get
        # a height of 0 when being displayed.
        sw.set_property('overlay_scrolling', False)
        self.vbox.pack_start(sw, True, True, 0)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.ALWAYS)

        self.textview = Gtk.TextView()
        self.textview.modify_font(Pango.FontDescription("Monospace 7"))
        sw.add(self.textview)
        self.buffer = self.textview.get_buffer()

        buttonbox = Gtk.HBox()
        self.vbox.pack_start(buttonbox, False, False, 3)

        self.b = Gtk.ToggleButton.new_with_label(_("Turn off"))
        self.b.set_active(True)
        buttonbox.pack_start(self.b, True, True, 3)
        self.b.connect("toggled", self._on_onoff__toggled)

        self.drawer = Gtk.ToggleButton.new_with_label(_("Open drawer"))
        self.drawer.set_active(True)
        buttonbox.pack_start(self.drawer, True, True, 3)
        self.drawer.connect("toggled", self._on_open_drawer__toggled)

        self.show_all()

    def _on_onoff__toggled(self, button):
        assert self._printer
        if button.get_active():
            self.b.set_label(_("Turn off"))
            self._printer.set_off(False)
        else:
            self.b.set_label(_("Turn on"))
            self._printer.set_off(True)

    def _on_open_drawer__toggled(self, button):
        assert self._printer
        if button.get_active():
            self.drawer.set_label(_("Close drawer"))
            self._printer.open_drawer()
        else:
            self.drawer.set_label(_("Open drawer"))
            self._printer.close_drawer()

    def feed(self, text):
        if isinstance(text, bytes):
            text = text.decode()
        position = self.buffer.get_end_iter()
        self.buffer.insert(position, text)

        mark = self.buffer.get_insert()
        self.textview.scroll_mark_onscreen(mark)


@implementer(ICouponPrinter, INonFiscalPrinter)
class Simple(object):

    model_name = "Virtual Printer"
    coupon_printer_charset = "utf-8"

    identify_customer_at_end = False
    supported = False
    max_characters = 72

    def __init__(self, port, consts=None):
        self._consts = consts or FakeConstants()
        self._customer_document = None

        # Internal state
        self.till_closed = False
        self.opening_date = datetime.date.today()
        self.serial = 'Serial'
        self.serial_id = '1234567890'
        self.coupon_start = 0
        self.coupon_end = 10
        self.cro = 1
        self.crz = 1
        self.coo = 1
        self.gnf = 1
        self.ccf = 1
        self.period_total = 0
        self.total = 0
        self.taxes = []

        self._reset_flags()
        self._load_state()

    #
    # Helper methods
    #

    def _print_coupon_header(self):
        self.write(
            "Virtual Printer\n"
            "Test Company\n"
            "CNPJ: 00.000.000/0000-00 IE: ISENTO\n"
            "IM: 012345\n")
        self._feed_line()
        self.write("%s  COO:%s\n" % (
            datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            self.coo))
        self._feed_line()

    def _get_state_filename(self):
        dirname = os.path.join(os.environ['HOME'], '.stoq')
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        filename = os.path.join(dirname, 'virtual-printer.json')
        return filename

    def _load_state(self):
        filename = self._get_state_filename()
        try:
            fp = open(filename, 'r')
        except (OSError, IOError):
            return
        try:
            state = json.load(fp)
        except ValueError:
            return

        self.till_closed = state['till-closed']

        fp.close()

    def _save_state(self):
        filename = self._get_state_filename()
        try:
            fp = open(filename, 'w')
        except (OSError, IOError):
            return

        state = {}
        state['till-closed'] = self.till_closed

        json.dump(state, fp)
        fp.write('\n')
        fp.close()

    def set_off(self, off):
        global _printer_off
        _printer_off = off

    def _check(self):
        if _printer_off:
            raise PrinterOfflineError

    def _reset_flags(self):
        self.is_coupon_opened = False
        self.items_quantity = 0
        self.is_coupon_totalized = False
        self.totalized_value = Decimal("0.0")
        self.has_payments = False
        self.payments_total = Decimal("0.0")
        self._items = {}
        self._is_centralized = False

    def _check_coupon_is_opened(self):
        if not self.is_coupon_opened:
            raise CouponOpenError(_("There is no coupon opened!"))

    def _check_coupon_is_closed(self):
        if self.is_coupon_opened:
            raise CouponOpenError(_("There is a coupon already open"))

    def _feed_line(self):
        self.write(('-' * self.max_characters) + '\n')

    def open_drawer(self):
        global _drawer_open
        _drawer_open = True
        OutputWindow.get_instance().drawer.set_label(_("Close drawer"))

    def close_drawer(self):
        global _drawer_open
        _drawer_open = False
        OutputWindow.get_instance().drawer.set_label(_("Open drawer"))

    def is_drawer_open(self):
        return _drawer_open

    #
    #   SerialBase implementation
    #

    def write(self, data):
        output = OutputWindow.get_instance()
        output.set_printer(self)
        output.feed(data)

    #
    # ICouponPrinter implementation
    #

    def setup(self):
        pass

    def has_open_coupon(self):
        return self.is_coupon_opened

    def coupon_identify_customer(self, customer, address, document):
        self._check()
        self._customer_name = customer
        self._customer_document = document
        self._customer_address = address

    def coupon_is_customer_identified(self):
        return self._customer_document is not None

    def coupon_open(self):
        self._check()
        self.write('\n')
        self.write("CUPOM SIMULADO\n")

        self.write("ITEM CODIGO DESCRICAO QTD.UN.VL. UNIT R$ ST A/T VL ITEM R$\n")
        self._check_coupon_is_closed()
        self.is_coupon_opened = True

    def coupon_add_item(self, code, description, price, taxcode,
                        quantity=Decimal("1.0"), unit=UnitType.EMPTY,
                        discount=Decimal("0.0"),
                        surcharge=Decimal("0.0"), unit_desc=""):
        self._check()
        self._check_coupon_is_opened()
        if self.is_coupon_totalized:
            raise ItemAdditionError(_("The coupon is already totalized, "
                                      "you can't add items anymore."))
        self.items_quantity += 1
        item_id = self.items_quantity
        item = CouponItem(item_id, quantity, price)
        self._items[item_id] = item
        self.write("%03d %s %s\n" % (self.items_quantity, code, description))
        self.write("  %d %f %s\n" % (quantity, price, taxcode))
        return item_id

    def coupon_cancel_item(self, item_id):
        self._check()
        self._check_coupon_is_opened()
        if item_id not in self._items:
            raise CancelItemError(_("There is no item with this ID (%d)")
                                  % item_id)
        elif self.is_coupon_totalized:
            raise CancelItemError(_("The coupon is already totalized, "
                                    "you can't cancel items anymore."))
        self._items.pop(item_id)
        self.write('cancel_item %r\n' % (item_id, ))

    def coupon_cancel(self):
        self._check()
        self._feed_line()
        self.write('    Cupom Cancelado\n')
        self._feed_line()
        self._reset_flags()

    def coupon_totalize(self, discount=Decimal("0.0"),
                        surcharge=Decimal("0.0"), taxcode=TaxType.NONE):
        # FIXME: API changed: discount/surcharge was percentage, now is Decimal.
        self._check()
        self._check_coupon_is_opened()
        if not self.items_quantity:
            raise CouponTotalizeError(_("The coupon can't be totalized, since "
                                        "there is no items added"))
        elif self.is_coupon_totalized:
            raise CouponTotalizeError(_("The coupon is already totalized"))

        for item_id, item in self._items.items():
            self.totalized_value += item.get_total_value()

        surcharge_value = self.totalized_value * surcharge / 100
        discount_value = self.totalized_value * discount / 100
        self.totalized_value += (
            Decimal(-discount_value).quantize(Decimal('.01')) +
            Decimal(surcharge_value).quantize(Decimal('.01')))

        if not self.totalized_value > 0:
            raise CouponTotalizeError(_("Coupon totalized must be greater "
                                        "than zero!"))

        self.is_coupon_totalized = True
        self.write('\n')
        self.write('Pagamentos:\n')
        return self.totalized_value

    def coupon_add_payment(self, payment_method, value, description=u"",
                           custom_pm=""):
        self._check()
        if not self.is_coupon_totalized:
            raise PaymentAdditionError(_("Isn't possible add payments to the "
                                         "coupon since it isn't totalized"))
        self.payments_total += value
        self.has_payments = True
        self.write('  %s - %s\n' % (
            self._consts._payment_descriptions[payment_method], value))
        return self.totalized_value - self.payments_total

    def coupon_close(self, message=''):
        self._check()
        self._check_coupon_is_opened()
        if not self.is_coupon_totalized:
            raise CloseCouponError(_("Isn't possible close the coupon "
                                     "since it isn't totalized yet!"))
        elif not self.has_payments:
            raise CloseCouponError(_("Isn't possible close the coupon "
                                     "since there is no payments added."))
        elif self.totalized_value > self.payments_total:
            raise CloseCouponError(_("The payments total value doesn't "
                                     "match the totalized value."))
        troco = self.payments_total - self.totalized_value
        if troco:
            self.write('Troco: %0.2f\n' % troco)
        self._feed_line()
        if message:
            self.write(message)
        self.write('\n')
        self._reset_flags()
        return 0

    def get_capabilities(self):
        self._check()
        # fake values
        return dict(item_code=Capability(max_len=48),
                    item_id=Capability(max_size=32767),
                    items_quantity=Capability(digits=14, decimals=4),
                    item_price=Capability(digits=14, decimals=4),
                    item_description=Capability(max_len=200),
                    payment_value=Capability(digits=14, decimals=4),
                    promotional_message=Capability(max_len=492),
                    payment_description=Capability(max_len=80),
                    customer_name=Capability(max_len=30),
                    customer_id=Capability(max_len=29),
                    customer_address=Capability(max_len=80),
                    cheque_thirdparty=Capability(max_len=45),
                    cheque_value=Capability(digits=14, decimals=4),
                    cheque_city=Capability(max_len=27))

    def get_constants(self):
        self._check()
        return self._consts

    def summarize(self):
        self._check()
        self.write('LEITURA X\n')
        self._feed_line()
        self.till_closed = False
        self._save_state()

    def open_till(self):
        self.summarize()

    def close_till(self, previous_day=False):
        self._check()
        if self.till_closed:
            raise DriverError(
                "Reduce Z was already sent today, try again tomorrow")
        self.till_closed = True
        self._save_state()
        self.write("REDUÇÃO Z\n")
        self._feed_line()

    def till_add_cash(self, value):
        self.write('SUPRIMENTO: %s\n' % value)
        self._feed_line()
        self._check()

    def till_remove_cash(self, value):
        self.write('SANGRIA: %s\n' % value)
        self._feed_line()
        self._check()

    def till_read_memory(self, start, end):
        self.write('LEITURA MF\n')
        self._feed_line()
        self._check()

    def till_read_memory_by_reductions(self, start, end):
        self.write('LEITURA MF\n')
        self._feed_line()
        self._check()

    def query_status(self):
        self._check()
        return None

    def get_serial(self):
        self._check()
        return 'Virtual'

    def get_tax_constants(self):
        self._check()
        return self._consts._tax_constants

    def get_payment_constant(self, payment):
        self._check()
        print('payment', payment)

    def get_payment_constants(self):
        self._check()
        return [(key, value) for key, value in
                self._consts._payment_descriptions.items()]

    def get_port(self):
        self._check()
        return None

    def has_pending_reduce(self):
        self._check()
        return False

    def get_coo(self):
        self._check()
        return self.coo

    def get_gnf(self):
        self._check()
        return self.gnf

    def get_ccf(self):
        self._check()
        return self.ccf

    def get_sintegra(self):
        self._check()
        return SintegraData(opening_date=self.opening_date,
                            serial=self.serial,
                            serial_id=self.serial_id,
                            coupon_start=self.coupon_start,
                            coupon_end=self.coupon_end,
                            cro=self.cro,
                            crz=self.crz,
                            coo=self.coo,
                            period_total=self.period_total,
                            total=self.total,
                            taxes=self.taxes)

    def get_crz(self):
        return self.crz

    # Receipt

    def get_payment_receipt_identifier(self, method_name):
        self._check()
        return None

    def payment_receipt_open(self, identifier, coo, method, value):
        self.write("    RECIBO DE PAGAMENTO coo=%s\n" % coo)

    def payment_receipt_print(self, text):
        self._check()
        self.write(text)

    def payment_receipt_close(self):
        self._check()
        self._feed_line()

    def gerencial_report_open(self, gerencial_id=0):
        self._check()
        self.write('      RELATORIO GERENCIAL\n\n')

    def gerencial_report_print(self, text):
        self._check()
        self.write(text)

    def gerencial_report_close(self):
        self._check()
        self._feed_line()

    def get_firmware_version(self):
        return '1.1.1'

    #
    # IChequePrinter implementation
    #

    def print_cheque(self, value, thirdparty, city, date=None):
        return

    #
    # INonFiscalPrinter implementation
    #

    def centralize(self):
        self._is_centralized = True

    def descentralize(self):
        self._is_centralized = False

    def set_bold(self):
        self._is_bold = True

    def unset_bold(self):
        self._is_bold = False

    def set_condensed(self):
        self._is_condensed = True

    def unset_condensed(self):
        self._is_condensed = False

    def set_double_height(self):
        self._is_double_height = True

    def unset_double_height(self):
        self._is_double_height = False

    def print_line(self, data):
        self._check()
        if self._is_centralized:
            data = data.center(self.max_characters)
        self.write(data + b'\n')

    def print_inline(self, data):
        self._check()
        self.write(data)

    def print_barcode(self, code):
        self.write('=== BARCODE {} ===\n'.format(code))

    def print_qrcode(self, code):
        self.write('=== QRCODE {} ===\n'.format(code))

    def cut_paper(self):
        self.write('\n--- paper cut ---\n')
