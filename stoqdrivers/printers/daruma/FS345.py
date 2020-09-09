# -*- Mode: Python; coding: iso-8859-1 -*-
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
"""
Daruma FS345 driver
"""

import datetime
from decimal import Decimal
import logging
import time

from zope.interface import implementer

from stoqdrivers import abicomp
from stoqdrivers.enum import TaxType, UnitType
from stoqdrivers.exceptions import (DriverError, PendingReduceZ,
                                    HardwareFailure, ReduceZError,
                                    AuthenticationFailure, CouponNotOpenError,
                                    OutofPaperError, PrinterOfflineError,
                                    CouponOpenError, CancelItemError,
                                    CloseCouponError)
from stoqdrivers.interfaces import ICouponPrinter
from stoqdrivers.printers.base import BaseDriverConstants
from stoqdrivers.printers.capabilities import Capability
from stoqdrivers.printers.fiscal import SintegraData
from stoqdrivers.serialbase import SerialBase
from stoqdrivers.translation import stoqdrivers_gettext
from stoqdrivers.utils import encode_text, decode_text

abicomp.register_codec()

_ = stoqdrivers_gettext

log = logging.getLogger('stoqdrivers.daruma')

CMD_STATUS = '\x1d\xff'

CMD_SET_OWNER = 190
# [ESC] 191 Grava��o da indica��o de mudan�a de moeda
# [ESC] 192 Interven��o T�cnica
CMD_GET_MODEL = 195
CMD_GET_FIRMWARE = 199
CMD_OPEN_COUPON = 200
CMD_IDENTIFY_CUSTOMER = 201
CMD_ADD_ITEM_1L6D = 202
CMD_ADD_ITEM_2L6D = 203
CMD_ADD_ITEM_3L6D = 204
CMD_CANCEL_ITEM = 205
# [ESC] 206 Cancelamento de Documento
CMD_CANCEL_COUPON = 206
CMD_GET_X = 207
CMD_REDUCE_Z = 208
CMD_READ_MEMORY = 209
# [ESC] 210 Emiss�o de Cupom Adicional
# [ESC] 211 Abertura de Relat�rio Gerencial (Leitura X)
CMD_GERENCIAL_REPORT_OPEN = 211
CMD_GERENCIAL_REPORT_CLOSE = 212
CMD_GERENCIAL_REPORT_PRINT = 213
CMD_CLOSE_NON_FISCAL_BOUND_RECEIPT = 212        # Pg. 37
CMD_PRINT_LINE_NON_FISCAL_BOUND_RECEIPT = 213   # Pg. 37
CMD_ADD_ITEM_1L13D = 214
CMD_ADD_ITEM_2L13D = 215
CMD_ADD_ITEM_3L13D = 216
CMD_OPEN_VOUCHER = 217
CMD_DESCRIBE_MESSAGES = 218
CMD_OPEN_NON_FISCAL_BOUND_RECEIPT = 219  # Pg 36
CMD_CONFIGURE_TAXES = 220
CMD_LAST_RECORD = 221
# [ESC] 223 Descri��o de produto em 3 linhas com c�digo de 13 d�gitos
#           (Formato fixo p/ Quantidade 5,3)
CMD_ADD_ITEM_3L13D53U = 223
# [ESC] 225 Descri��o de produto com pre�o unit�rio com 3 decimais
CMD_DESCRIBE_NON_FISCAL_RECEIPT = 226   # Pg. 42
# [ESC] 227 Subtotaliza��o de Cupom Fiscal
# [ESC] 228 Configura��o da IF
CMD_GET_CONFIGURATION = 229
# [ESC] 230 Leitura do rel�gio interno da impressora
CMD_GET_TAX_CODES = 231
# [ESC] 232 Leitura do clich� do propriet�rio
# [ESC] 234 Retransmiss�o de mensagens da IF
CMD_GET_IDENTIFIER = 236
CMD_GET_PERSONAL_MESSAGES = 238
CMD_GET_DOCUMENT_STATUS = 239
CMD_GET_FISCAL_REGISTRIES = 240
CMD_TOTALIZE_COUPON = 241
CMD_DESCRIBE_PAYMENT_FORM = 242
CMD_CLOSE_COUPON = 243
CMD_GET_REGISTRIES = 244
CMD_GET_TOTALIZERS = 244
# [ESC] 246 Leitura Hor�ria
# [ESC] 247 Descri��o Estendida
# [ESC] 248 Estorno de forma de pagamento
CMD_GET_DATES = 250
# [ESC] 251 Leitura das informa��es cadastrais do usu�rio
# [ESC] V   Controle de hor�rio de ver�o

CASH_IN_TYPE = 'B'
CASH_OUT_TYPE = 'A'

RETRIES_BEFORE_TIMEOUT = 5

# Document status
OPENED_FISCAL_COUPON = '1'
CLOSED_COUPON = '2'


def isbitset(value, bit):
    # BCD crap
    return (int(value, 16) >> bit) & 1 == 1


def ifset(value, bit, false='', true=''):
    if not isbitset(value, bit):
        return false
    else:
        return true


class FS345Constants(BaseDriverConstants):
    _constants = {
        UnitType.WEIGHT: 'Kg',
        UnitType.METERS: 'm ',
        UnitType.LITERS: 'Lt',
        UnitType.EMPTY: '  ',
    }


@implementer(ICouponPrinter)
class FS345(SerialBase):
    log_domain = 'fs345'

    supported = True
    model_name = "Daruma FS 345"
    coupon_printer_charset = "abicomp"
    supports_duplicate_receipt = False
    identify_customer_at_end = True

    def __init__(self, port, consts=None):
        self._consts = consts or FS345Constants
        SerialBase.__init__(self, port)
        self._reset()

    def _reset(self):
        self._customer_name = u""
        self._customer_document = u""
        self._customer_address = u""

    def send_command(self, command, extra=''):
        raw = chr(command) + extra
        while True:
            self.write(self.CMD_PREFIX + raw + self.CMD_SUFFIX)
            retval = self._read_reply()
            if retval.startswith(':E'):
                try:
                    self.handle_error(retval, raw)
                except DriverError as e:
                    if e.code == 42:
                        self.send_command(CMD_GET_X)
                        continue
                    raise
            break

        return retval[1:]

    def _read_reply(self):
        rep = ''
        timeouts = 0

        while True:
            if timeouts > RETRIES_BEFORE_TIMEOUT:
                raise DriverError(_("Timeout communicating with fiscal "
                                    "printer"))

            c = self.read(1)
            if len(c) != 1:
                timeouts += 1
                continue

            if c == self.EOL_DELIMIT:
                log.debug("<<< %r" % rep)
                return rep

            rep += c

    # Status
    def _get_status(self):
        self.write(CMD_STATUS)
        return self._read_reply()

    def status_check(self, S, byte, bit):
        return isbitset(S[byte], bit)

    def _check_status(self, verbose=False):
        status = self._get_status()
        if status[0] != ':':
            raise HardwareFailure('Broken status reply')

        if verbose:
            print('== STATUS ==')

            # Codes found on page 57-59
            print('Raw status code:', status)
            print('Cashier drawer is', ifset(status[1], 3, 'closed', 'open'))

        if self.has_pending_reduce():
            raise PendingReduceZ(_('Pending Reduce Z'))
        if self.status_check(status, 1, 2):
            raise HardwareFailure(_('Mechanical failure'))
        if not self.status_check(status, 1, 1):
            raise AuthenticationFailure(_('Not properly authenticated'))
        if self.status_check(status, 1, 0):
            raise OutofPaperError(_('No paper'))
        if self.status_check(status, 2, 3):
            raise PrinterOfflineError(_("Offline"))
        if self.status_check(status, 2, 0):
            log.info('Almost out of paper')

        if verbose:
            S3 = status[3]
            print(ifset(S3, 3, 'Maintenance', 'Operational'), 'mode')
            print('Authentication', ifset(S3, 2, 'disabled', 'enabled'))
            print('Guillotine', ifset(S3, 1, 'disabled', 'enabled'))
            print('Auto close CF?', ifset(S3, 0, 'no', 'yes'))

        if self.status_check(status, 6, 1):
            raise ReduceZError(_("readZ is already emitted"))

        return status

    def has_pending_reduce(self, status=None):
        if not status:
            status = self._get_status()
        return self.status_check(status, 2, 1)

    def needs_read_x(self, status=None):
        if not status:
            status = self._get_status()

        return not self.status_check(status, 6, 2)

    # Error handling

    def handle_error(self, error_value, raw):
        error = int(error_value[2:])
        # Page 61-62
        if error == 39:
            raise DriverError('Bad parameters: %r' % raw, error)
        elif error == 10:
            raise CouponOpenError(_("Document is already open"), error)
        elif error == 11:
            raise CouponNotOpenError(_("Coupon is not open"), error)
        elif error == 12:
            raise CouponNotOpenError(_("There's no open document to cancel"),
                                     error)
        elif error == 15:
            raise CancelItemError(_("There is no such item in "
                                    "the coupon"), error)
        elif error == 16:
            raise DriverError("Bad discount/markup parameter", error)
        elif error == 21:
            log.warning(_('Printer error %s: No paper'), error)
        elif error == 22:
            raise DriverError(
                "Reduce Z was already sent today, try again tomorrow", error)
        elif error == 23:
            raise PendingReduceZ
        elif error == 24:
            raise DriverError("Bad unit specified: %r" % raw, error)
        elif error == 42:
            raise DriverError("Read X has not been sent yet", error)
        elif error == 45:
            raise DriverError(_("Required field is blank"), error)
        else:
            raise DriverError("Unhandled error: %d" % error, error)

    # Information / debugging

    def show_status(self):
        self._check_status(verbose=True)

    def show_information(self):
        print('Model:', self.send_command(CMD_GET_MODEL))
        print('Firmware:', self.send_command(CMD_GET_FIRMWARE))
        data = self.send_command(CMD_LAST_RECORD)

        tt = time.strptime(data[:12], '%d%m%y%H%M%S')
        print('Last record:', time.strftime('%c', tt))
        print('Configuration:', self.send_command(CMD_GET_CONFIGURATION))

    def show_document_status(self):
        print('== DOCUMENT STATUS ==')
        value = self._get_document_status()
        print('ECF:', value[2:6])
        document_type = value[6]
        if document_type == CLOSED_COUPON:
            print('No open coupon')
        elif document_type == OPENED_FISCAL_COUPON:
            print('Document is a coupon (%s)' % value[7:12])
        else:
            print('Document type:', value[6])

        tt = time.strptime(value[13:27], '%H%M%S%d%m%Y')
        print('Current date/time:', time.strftime('%c', tt))

        print('Sum', int(value[27:41]) / 100.0)
        print('GT atual', value[41:59])

    def _get_document_status(self):
        status = self.send_command(CMD_GET_DOCUMENT_STATUS)
        assert status[:2] == '\x1b' + chr(CMD_GET_DOCUMENT_STATUS)
        assert len(status) == 59
        return status

    def get_firmware_version(self):
        """Return the firmware version."""
        return self.send_command(CMD_GET_FIRMWARE)

    def _get_fiscal_registers(self):
        value = self.send_command(CMD_GET_FISCAL_REGISTRIES)
        assert value[:2] == '\x1b' + chr(CMD_GET_FISCAL_REGISTRIES)
        return value[2:]

    def _get_registers(self):
        value = self.send_command(CMD_GET_REGISTRIES)
        assert value[:2] == '\x1b' + chr(CMD_GET_REGISTRIES)
        return value[2:]

    # High level commands
    def _verify_coupon_open(self):
        if not self.status_check(self._get_status(), 4, 2):
            raise CouponNotOpenError(_("Coupon is not open"))

    def _is_open(self, status):
        return self.status_check(status, 4, 2)

    # Helper commands

    def _get_totalizers(self):
        return self.send_command(CMD_GET_TOTALIZERS)

    def _get_coupon_number(self):
        return int(self._get_totalizers()[8:14])

    def _add_payment(self, payment_method, value, description=''):
        rv = self.send_command(CMD_DESCRIBE_PAYMENT_FORM,
                               '%c%012d%s\xff' % (payment_method,
                                                  int(value * Decimal('1e2')),
                                                  description[:48]))
        # FIXME: Why and when does this happen?
        #        Avoids/Fixes bug 3467 at least
        if rv[0] == 'N':
            rv = rv[8:]
        return Decimal(rv) / Decimal('1e2')

    def _add_voucher(self, type, value):
        data = "%s1%s%012d\xff" % (type, "0" * 12,  # padding
                                   int(value * Decimal('1e2')))
        self.send_command(CMD_OPEN_VOUCHER, data)

    def _configure_taxes(self):
        self.send_command(CMD_CONFIGURE_TAXES, '1800')
        self.send_command(CMD_CONFIGURE_TAXES, '1500')
        self.send_command(CMD_CONFIGURE_TAXES, '2500')
        self.send_command(CMD_CONFIGURE_TAXES, '0800')
        self.send_command(CMD_CONFIGURE_TAXES, '0500')
        self.send_command(CMD_CONFIGURE_TAXES, '0327')
        self.send_command(CMD_CONFIGURE_TAXES, '0592')
        self.send_command(CMD_CONFIGURE_TAXES, 'S0200')
        self.send_command(CMD_CONFIGURE_TAXES, 'S0300')
        self.send_command(CMD_CONFIGURE_TAXES, 'S0400')

    def _configure_payment_methods(self):
        self.send_command(CMD_DESCRIBE_MESSAGES, 'PGXADinheiro         ')
        self.send_command(CMD_DESCRIBE_MESSAGES, 'PGXBCheque           ')
        self.send_command(CMD_DESCRIBE_MESSAGES, 'PGXCBoleto           ')
        self.send_command(CMD_DESCRIBE_MESSAGES, 'PGVDCartao Credito   ')
        self.send_command(CMD_DESCRIBE_MESSAGES, 'PGVECartao Debito    ')
        self.send_command(CMD_DESCRIBE_MESSAGES, 'PGVFFinanceira       ')
        self.send_command(CMD_DESCRIBE_MESSAGES, 'PGVGVale Compra      ')

    def _configure_bound_receipts(self):
        self.send_command(CMD_DESCRIBE_NON_FISCAL_RECEIPT, 'VCartao Credito       ')

    #
    # API implementation
    #

    def setup(self):
        pass

    def coupon_identify_customer(self, customer, address, document):
        self._customer_name = customer
        self._customer_document = document
        self._customer_address = address

    def coupon_is_customer_identified(self):
        return len(self._customer_document) > 0

    def has_open_coupon(self):
        status = self._get_document_status()
        coupon_status = status[6]
        return coupon_status != CLOSED_COUPON

    def coupon_open(self):
        status = self._check_status()
        if self._is_open(status):
            raise CouponOpenError(_("Coupon already open"))
        self.send_command(CMD_OPEN_COUPON)

    def coupon_add_item(self, code, description, price, taxcode,
                        quantity=Decimal("1.0"), unit=UnitType.EMPTY,
                        discount=Decimal("0.0"),
                        surcharge=Decimal("0.0"), unit_desc=""):
        if surcharge:
            d = 1
            E = surcharge
        else:
            d = 0
            E = discount

        if unit == UnitType.CUSTOM:
            unit = unit_desc
        else:
            unit = self._consts.get_value(unit)

        if not code:
            code = "-"
        data = '%2s%13s%d%04d%010d%08d%s%s\xff' % (taxcode, code[:13], d,
                                                   int(E * Decimal('1e2')),
                                                   int(price * Decimal('1e3')),
                                                   int(quantity * Decimal('1e3')),
                                                   unit, description[:174])
        value = self.send_command(CMD_ADD_ITEM_3L13D53U, data)
        return int(value[1:4])

    def coupon_cancel_item(self, item_id):
        self.send_command(CMD_CANCEL_ITEM, "%03d" % item_id)

    def coupon_add_payment(self, payment_method, value, description=''):
        self._check_status()
        self._verify_coupon_open()
        return self._add_payment(payment_method, value, description)

    def coupon_cancel(self):
        # If we need reduce Z don't verify that the coupon is open, instead
        # just cancel the coupon. This avoids a race when you forgot
        # to close a coupon and reduce Z at the same time.
        if not self.has_pending_reduce():
            self._check_status()
        self.send_command(CMD_CANCEL_COUPON)

    def cancel_last_coupon(self):
        """Cancel the last non fiscal coupon or the last sale."""
        self.send_command(CMD_CANCEL_COUPON)

    def coupon_totalize(self, discount=Decimal(0), surcharge=Decimal(0),
                        taxcode=TaxType.NONE):
        self._check_status()
        self._verify_coupon_open()
        if surcharge:
            value = surcharge
            if taxcode == TaxType.ICMS:
                mode = 3
            else:
                raise ValueError("tax_code must be TaxType.ICMS")
        elif discount:
            value = discount
            mode = 1
        else:
            mode = 1
            value = Decimal(0)
        # Page 33
        data = '%s%012d' % (mode, int(value * Decimal("1e2")))
        rv = self.send_command(CMD_TOTALIZE_COUPON, data)
        return Decimal(rv) / Decimal("1e2")

    def coupon_close(self, message=''):
        self._check_status()
        self._verify_coupon_open()

        if (self._customer_name or self._customer_address or self._customer_document):
            customer_name = self._customer_name or _("No client")
            customer_document = self._customer_document or _("No document")
            customer_address = self._customer_address or _("No address")
            self.send_command(CMD_IDENTIFY_CUSTOMER,
                              "%- 84s%- 84s%- 84s" % (customer_name,
                                                      customer_address,
                                                      customer_document))
        # NOTE: Do not try to encode the message again. It was already
        # encoded by printers.fiscal before. By doing that we would be
        # encoding it twice.
        try:
            self.send_command(CMD_CLOSE_COUPON, message + '\xff')
        except DriverError:
            raise CloseCouponError(_("It is not possible to close the "
                                     "coupon"))
        self._reset()
        return self._get_coupon_number()

    def summarize(self):
        self.send_command(CMD_GET_X)

    def open_till(self):
        self.summarize()

    def close_till(self, previous_day=False):
        status = self._get_status()
        if self._is_open(status):
            self.send_command(CMD_CANCEL_COUPON)

        date = time.strftime('%d%m%y%H%M%S', time.localtime())
        self.send_command(CMD_REDUCE_Z, date)

    def _get_bound_receipt_constants(self):
        # Also page 48
        messages = self.send_command(CMD_GET_PERSONAL_MESSAGES)

        raw = messages[372:708]
        constants = []
        const_letter = 'ABCDEFGHIJKLMNOP'
        for i, char in enumerate(const_letter):
            const = raw[i * 21:i * 21 + 21]
            # Ignore constants that are not registered.
            if const[2] == '\xff':
                continue

            const = decode_text(const, self.coupon_printer_charset)
            constants.append((char, const.strip()))

        return constants

    def get_payment_receipt_identifier(self, method_name):
        """Returns the receipt identifier corresponding to the payment method.

        @param method_name: this is the payment method name. A receipt with
                            the same name should be configured at the printer.
        """
        constants = self._get_bound_receipt_constants()
        for id, name in constants:
            if name == method_name:
                return id

        raise DriverError(_("Receipt for method %s is not configured") % method_name)

    def payment_receipt_open(self, identifier, coo, method, value):
        value = int(value * 100)
        # res is the coo for the current document.
        self.send_command(CMD_OPEN_NON_FISCAL_BOUND_RECEIPT,
                          '%c%c%06d%012d' % (identifier, method, coo, value))

    def payment_receipt_print(self, text):
        for line in text.split('\n'):
            self.send_command(CMD_PRINT_LINE_NON_FISCAL_BOUND_RECEIPT,
                              line + chr(255))

    def payment_receipt_close(self):
        self.send_command(CMD_CLOSE_NON_FISCAL_BOUND_RECEIPT)

    def gerencial_report_open(self):
        self.send_command(CMD_GERENCIAL_REPORT_OPEN)

    def gerencial_report_print(self, text):
        for line in text.split('\n'):
            self.send_command(CMD_GERENCIAL_REPORT_PRINT, line + chr(255))

    def gerencial_report_close(self):
        self.send_command(CMD_GERENCIAL_REPORT_CLOSE)

    def till_add_cash(self, value):
        self._add_voucher(CASH_IN_TYPE, value)
        self._add_payment('A', value, '')

    def till_remove_cash(self, value):
        self._add_voucher(CASH_OUT_TYPE, value)

    def till_read_memory(self, start, end):
        # Page 39
        self.send_command(CMD_READ_MEMORY, 'x%s%s' % (start.strftime('%d%m%y'),
                                                      end.strftime('%d%m%y')))

    def _till_read_memory_to_serial(self, start, end):
        # Page 39
        ret = self.send_command(CMD_READ_MEMORY, 's%s%s' % (start.strftime('%d%m%y'),
                                                            end.strftime('%d%m%y')))
        data = ''
        while True:
            line = self.readline()
            if line[-1] == '\xff':
                break
            data += line

        data = encode_text(data, 'cp860')
        return (ret, data)

    def till_read_memory_by_reductions(self, start, end):
        # Page 39
        self.send_command(CMD_READ_MEMORY, 'x00%04d00%04d' % (start, end))

    def get_capabilities(self):
        return dict(item_code=Capability(max_len=13),
                    item_id=Capability(digits=3),
                    items_quantity=Capability(min_size=1, digits=5, decimals=3),
                    item_price=Capability(min_size=0, digits=7, decimals=3),
                    item_description=Capability(max_len=173),
                    payment_value=Capability(digits=10, decimals=2),
                    promotional_message=Capability(max_len=384),
                    payment_description=Capability(max_len=48),
                    customer_name=Capability(max_len=42),
                    customer_id=Capability(max_len=42),
                    customer_address=Capability(max_len=42),
                    remove_cash_value=Capability(min_size=1, digits=10,
                                                 decimals=2),
                    add_cash_value=Capability(min_size=1, digits=10,
                                              decimals=2))

    def get_constants(self):
        return self._consts

    def query_status(self):
        return CMD_STATUS

    def status_reply_complete(self, reply):
        return '\r' in reply

    def get_serial(self):
        identifier = self.send_command(CMD_GET_IDENTIFIER)
        return identifier[1:9]

    def get_ccf(self):
        # Daruma FS345 does not have ccf. See:
        # http://www.forumweb.com.br/foruns/lofiversion/index.php/t64417.html
        return self.get_coo()

    def get_coo(self):
        registries = self._get_registers()
        return int(registries[7:12])

    def get_gnf(self):
        registries = self._get_registers()
        return int(registries[13:18])

    def get_crz(self):
        registries = self._get_registers()
        return int(registries[38:42])

    def get_tax_constants(self):
        tax_codes = self.send_command(CMD_GET_TAX_CODES)[1:]

        constants = []
        for i in range(14):
            reg = tax_codes[i * 5]
            if reg in 'ABCDEFGHIJKLMNOP':
                tax_type = TaxType.CUSTOM
            elif reg in 'abcdefghijklmnop':
                tax_type = TaxType.SERVICE
            else:
                raise AssertionError(reg)
            value = tax_codes[i * 5 + 1:i * 5 + 5]
            if value == '////':
                continue
            constants.append((tax_type,
                              'T' + reg.lower(),
                              Decimal(value.replace('.', '')) / 100))

        # These definitions can be found on Page 60
        constants.extend([
            (TaxType.SUBSTITUTION, 'Fb', None),
            (TaxType.EXEMPTION, 'Ib', None),
            (TaxType.NONE, 'Nb', None),
        ])

        return constants

    def get_payment_constants(self):
        # Page 48
        messages = self.send_command(CMD_GET_PERSONAL_MESSAGES)

        raw = messages[708:]
        methods = []
        method_letter = 'ABCDEFGHIJKLMNOP'
        for i in range(16):
            method = raw[i * 18:i * 18 + 18]
            if method[2] == '\xff':
                continue

            name = decode_text(method[1:].strip(), self.coupon_printer_charset)
            methods.append((method_letter[i], name))

        return methods

    def get_sintegra(self):
        registries = self._get_registers()
        fiscal_registries = self._get_fiscal_registers()

        tax_codes = self.send_command(CMD_GET_TAX_CODES)[1:]

        taxes = []
        for i in range(14):
            reg = tax_codes[i * 5 + 1:i * 5 + 5]
            if reg == '////':
                continue
            reg = reg.replace('.', '')

            if tax_codes[i * 5] in 'ABCDEFGHIJKLMNOP':
                type = 'ICMS'
            else:
                type = 'ISS'

            sold = fiscal_registries[88 + (i * 14):102 + (i * 14)]
            taxes.append((reg, Decimal(sold) / 100, type))

        taxes.append(('DESC', Decimal(fiscal_registries[19:32]) / 100, 'ICMS'))
        taxes.append(('CANC', Decimal(fiscal_registries[33:46]) / 100, 'ICMS'))
        taxes.append(('I', Decimal(fiscal_registries[47:60]) / 100, 'ICMS'))
        taxes.append(('N', Decimal(fiscal_registries[61:74]) / 100, 'ICMS'))
        taxes.append(('F', Decimal(fiscal_registries[75:88]) / 100, 'ICMS'))

        total_sold = sum(value for _, value, _ in taxes)

        old_total = Decimal(fiscal_registries[:18]) / 100
        period_total = total_sold

        dates = self.send_command(CMD_GET_DATES)
        if dates[:6] == '000000':
            opening_date = datetime.date.today()
        else:
            d, m, y = list(map(int, [dates[:2], dates[2:4], dates[4:6]]))
            opening_date = datetime.date(2000 + y, m, d)

        identifier = self.send_command(CMD_GET_IDENTIFIER)
        return SintegraData(
            opening_date=opening_date,
            serial=identifier[1:9],
            serial_id=int(identifier[13:17]),
            coupon_start=int(registries[:6]),
            coupon_end=int(registries[6:12]),
            cro=int(registries[34:38]),
            crz=int(registries[38:42]),  # FIXME: this is being fetched before the actual
            # reduction, so it will offset by one.
            coo=int(registries[6:12]),
            period_total=period_total,
            total=period_total + old_total,
            taxes=taxes)
