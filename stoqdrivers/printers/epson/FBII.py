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
Epson FB II ECF driver
"""

import datetime
import logging
import struct
from decimal import Decimal

from kiwi.currency import currency
from kiwi.python import Settable
from zope.interface import implements

from stoqdrivers.serialbase import SerialBase
from stoqdrivers.interfaces import ICouponPrinter
from stoqdrivers.exceptions import (DriverError, PrinterError, CommandError,
                                    CommandParametersError, OutofPaperError,
                                    CancelItemError, AlmostOutofPaper,
                                    ItemAdditionError, CouponOpenError,
                                    CouponNotOpenError)
from stoqdrivers.enum import TaxType, UnitType
from stoqdrivers.printers.base import BaseDriverConstants
from stoqdrivers.translation import stoqdrivers_gettext

ACK = '\x06'
STX = '\x02'
ETX = '\x03'
ESC = '\x1b'
FLD = '\x1c'

# Special protocol chars that need to be escaped when communicating
SPECIAL_CHARS = [ESC, STX, ETX, FLD, '\x1a', '\x1d', '\x1e', '\x1f']


def escape(string):
    for i in SPECIAL_CHARS:
        string = string.replace(i, ESC + i)
    return string


def unescape(string):
    for i in SPECIAL_CHARS:
        string = string.replace(ESC + i, i)
    return string

FIRST_COMMAND_ID = 0x81
RETRIES_BEFORE_TIMEOUT = 5

# When cancel the last coupon. This values are used to define the coupon type.
FISCAL_COUPON = '1'
NON_FISCAL_COUPON = '24'

# Coupons status
CLOSED_COUPON = '0000'
OPENED_FISCAL_COUPON = '0001'
OPENED_NON_FISCAL_COUPON = '1000'

_ = stoqdrivers_gettext

log = logging.getLogger('stoqdrivers.epson')


class Reply(object):

    #
    #   Printer flags
    #

    error_codes = {
        '0101': (CommandError(_("Invalid command for current state."))),
        '0102': (CommandError(_("Invalid command for current document."))),
        '0203': (CommandError(_("Excess fields"))),
        '0204': (CommandError(_("Missing fields"))),
        '0205': (CommandParametersError(_("Field not optional."))),
        '0206': (CommandParametersError(_("Invalid alphanumeric field."))),
        '0207': (CommandParametersError(_("Invalid alphabetic field."))),
        '0208': (CommandParametersError(_("Invalid numeric field."))),
        '020E': (CommandParametersError(_("Fields with print invalid "
                                          "attributes."))),

        '0304': (OutofPaperError(_("Out of paper."))),
        '0305': (AlmostOutofPaper(_("Almost out of paper."))),

        '0801': (CommandError(_("Invalid command with closed "
                                "fiscal journey."))),

        '090C': (DriverError(_("Payment method not defined."))),
        '090F': (ItemAdditionError(_("Tax not found."))),
        '0910': (ItemAdditionError(_("Invalid tax."))),

        '0A12': (CancelItemError(_("It was not possible cancel the last "
                                   "fiscal coupon."))),
        '0A15': (PrinterError(_("Requires CDC cancellation."))),
        '0A16': (CancelItemError(_("Invalid item number in fiscal coupon"))),
        '0E0A': (PrinterError(_("Last non-fiscal coupon not found."))),
        '0E0B': (PrinterError(_("Payment method not found."))),
    }

    def __init__(self, string, command_id):
        checksum = string[-4:]
        self.string = string[:-4]

        log.debug('reply %s' % repr(string))
        cs = '%04X' % sum([ord(i) for i in self.string])
        if cs != checksum:
            raise DriverError('Erro de checksum')

        self.string = unescape(self.string)

        # Verifica header & tail
        assert self.pop() == STX, 'STX'
        frame_id = self.pop()
        if frame_id == '\x80':
            self.intermediate = True
            return

        self.intermediate = False
        assert frame_id == chr(command_id), ('command_id', command_id)
        assert self.string[-1] == ETX, 'ETX'

        # Retira statuses
        self.printer_status = struct.unpack('>H', self.pop(2))[0]
        assert self.pop() == FLD, 'FLD 1'
        self.fiscal_status = struct.unpack('>H', self.pop(2))[0]
        assert self.pop() == FLD, 'FLD 2'

        # reserved
        self.pop()

        r = self.pop(2)
        self.reply_status = '%02X%02X' % (ord(r[0]), ord(r[1]))

        assert self.pop() == FLD, 'FLD 3'
        # reserved
        self.pop()

        # Pega dados de retorno

        fields = self.string[:-1]

        # FIXME: Maybe we need to de-escape the string
        self.fields = fields.split(FLD)
        #for f in self.fields: print f

    def check_error(self):
        log.debug("reply_status %s" % self.reply_status)
        error_code = self.reply_status
        # Success, do nothing
        if error_code == '0000':
            return

        if error_code in self.error_codes:
            error = self.error_codes[error_code]
            error.code = int(error_code, 16)
            raise error

        raise DriverError(error="unhandled driver error",
                          code=int(error_code, 16))

    def pop(self, size=1):
        """Remove size bites from the begining of self.string and returns it
        """
        head = self.string[:size]
        self.string = self.string[size:]
        return head

    def check_printer_status(self):
        status = bin(self.printer_status)
        printer_status = status[2:]
        return printer_status

    def check_fiscal_status(self):
        status = bin(self.fiscal_status)
        fiscal_status = status[2:]
        return fiscal_status


class FBIIConstants(BaseDriverConstants):
    # The 'unit' field is mandatory in ECF.
    # If unit is EMPTY, set the value 'UN' to avoid errors.
    _constants = {
        UnitType.WEIGHT: 'Kg',
        UnitType.METERS: 'm',
        UnitType.LITERS: 'Lt',
        UnitType.EMPTY: 'UN',
    }


#
# The driver implementation
#

class FBII(SerialBase):

    implements(ICouponPrinter)

    supported = True
    identify_customer_at_end = True

    model_name = "Epson FBII"
    coupon_printer_charset = "ascii"

    def __init__(self, port, consts=None):
        SerialBase.__init__(self, port)
        self._consts = consts or FBIIConstants
        self._command_id = FIRST_COMMAND_ID - 1  # 0x80
        self._reset()

    def setup(self):
        # Get the decimal places from printer to use in price and quantity.
        data = self._send_command('0585')
        self._decimals_quantity = Decimal('1e' + data.fields[0])
        self._decimals_price = Decimal('1e' + data.fields[1])

    def _reset(self):
        self._customer_name = ''
        self._customer_document = ''
        self._customer_address = ''

    #
    # Helper methods
    #

    def _get_next_command_id(self):
        if self._command_id == 255:
            self._command_id = FIRST_COMMAND_ID - 1

        self._command_id += 1
        return chr(self._command_id)

    def _get_package(self, command, extension, args=None):
        # First, convert command and extention from string representation to hex
        command = '%s%s' % (chr(int(command[:2], 16)), chr(int(command[2:], 16)))
        extension = '%s%s' % (chr(int(extension[:2], 16)), chr(int(extension[2:], 16)))

        frame = escape(command) + FLD + escape(extension)

        if args:
            for i in args:
                frame += FLD + escape(i)

        command_id = self._get_next_command_id()
        package = STX + command_id + frame + ETX

        checksum = sum([ord(d) for d in package])
        return package + '%04X' % checksum

    def _read_reply(self):
        reply = ''
        timeouts = 0

        while True:
            if timeouts > RETRIES_BEFORE_TIMEOUT:
                raise DriverError(_("Timeout communicating with fiscal "
                                    "printer"))

            c = self.read(1)
            if len(c) != 1:
                timeouts += 1
                continue

            # STX is always the first char in the reply. Ignore garbage
            # until STX is received.
            if len(reply) == 0 and c != STX:
                log.info('ignoring garbage in reply: %r' % c)
                continue

            reply += c

            if c == ETX and reply[-2] != ESC:
                break

        reply += self.read(4)
        log.debug("<<< %s" % repr(reply))

        return Reply(reply, self._command_id)

    def _send_command(self, command, extension='0000', *args):
        cmd = self._get_package(command, extension, args)
        #log.debug("> %s" % repr(cmd))
        self.write(cmd)

        # Printer should reply with an ACK imediataly
        ack = self.read(1)
        if not ack:
            raise DriverError(_("Timeout communicating with fiscal "
                                "printer"))
        assert ack == ACK, repr(ack)

        reply = self._read_reply()

        # Keep reading while printer sends intermediate replies.
        while reply.intermediate:
            log.debug("intermediate")
            reply = self._read_reply()

        # send our ACK
        self.write(ACK)

        reply.check_error()
        return reply

    def _parse_price(self, value):
        # Valor retirado da ECF (string) convertido para decimal.
        return currency(value) / Decimal('1e2')

    #
    # ICouponPrinter implementation
    #

    # Printer Quering

    def query_status(self):
        cmd = self._get_package('0001', '0000')
        return cmd

    def status_reply_complete(self, reply):
        complete = len(reply) == 18
        if complete:
            self.write(ACK)
        return complete

    #
    #   Till Operations
    #

    def summarize(self):
        self._send_command('0802')

    def open_till(self):
        self._send_command('0805')

    def has_pending_reduce(self):
        # Dia encerrado e NÃO reduzido.
        pending_reduce_z = 4

        # Estado da jornada fiscal.
        reply = self._send_command('0810')
        return int(reply.fields[0]) == pending_reduce_z

    def close_till(self, previous_day=False):
        # Nesse momento é possível realizar ajustes no horário da ECF (como
        # entrar e sair do horário de verão. Podemos estudar implementar isso no
        # stoq.
        self._send_command('0801', '0000', '', '')

    def _add_voucher(self, type, value):
        # Abre comprovante não fiscal
        self._send_command('0E01', '0000', '')

        # Adiciona item
        value = int(value * Decimal('1e2'))
        self._send_command('0E15', '0000', type, str(value))

        # Fecha
        self._send_command('0E06')

    def till_add_cash(self, value):
        self._add_voucher('02', value)

    def till_remove_cash(self, value):
        self._add_voucher('01', value)

    def till_read_memory(self, start, end):
        self._send_command('0910', '0001', '', '', start.strftime('%d%m%Y'),
                           end.strftime('%d%m%Y'))

    def till_read_memory_by_reductions(self, start, end):
        self._send_command('0910', '0000', str(start), str(end), '', '')

    def get_sintegra(self):
        # Informações da jornada fiscal.
        reply = self._send_command('080A')
        # Data de abertura.
        date = reply.fields[0]
        d, m, y = map(int, [date[:2], date[2:4], date[4:8]])
        opening_date = datetime.date(y, m, d)
        # COO inicial.
        coupon_start = int(reply.fields[4])

        #Número sequencial da ECF.
        fiscal_data = self._send_command('0507')
        serial_id = int(fiscal_data.fields[8])

        # Obter totalizadores.
        ecf_totals = self._send_command('0906')
        # Totalizador venda bruta diária.
        value = ecf_totals.fields[1]
        period_total = currency(value) / Decimal('1e2')
        # Total Geral.
        geral = ecf_totals.fields[0]
        total = currency(geral) / Decimal('1e2')

        data = Settable(
            opening_date=opening_date,
            serial=self.get_serial(),
            serial_id=serial_id,
            coupon_start=coupon_start,
            coupon_end=self.get_coo(),
            cro=self.get_cro(),
            crz=self.get_crz(),
            coo=self.get_coo(),
            period_total=period_total,
            total=total,
            taxes=self._get_taxes(),
        )
        return data

    def get_payment_receipt_identifier(self, method_name):
        # We don't need a identifier. Just return None.
        return None

    def payment_receipt_open(self, identifier, coo, method, value):
        # FIXME: Verificar possibilidade de se implementar a utilização de
        # quantidade de parcelas.
        value = int(value * Decimal('1e2'))
        self._send_command('0E30', '0000', method, str(value), '1', str(coo))

    def payment_receipt_print(self, text):
        self._print_report_text(text)

    def payment_receipt_close(self):
        self._send_command('0E06')

    #
    # Coupon related commands
    #

    def coupon_identify_customer(self, customer, address, document):
        self._customer_name = customer
        self._customer_document = document
        self._customer_address = address

    def coupon_is_customer_identified(self):
        return len(self._customer_document) > 0

    def has_open_coupon(self):
        checked_coupon = self._get_coupon_status()
        return checked_coupon != CLOSED_COUPON

    def coupon_open(self):
        coupon_status = self._get_coupon_status()
        if coupon_status == OPENED_FISCAL_COUPON:
            raise CouponOpenError(_("Coupon already open"))
        self._send_command('0A01', '0000', '', '')

    def _cancel_fiscal_coupon(self):
        self._send_command('0A18', '0008', '1')

    def _cancel_non_fiscal_coupon(self):
        self._send_command('0E18', '0008', '1')

    def coupon_cancel(self):
        checked_coupon = self._get_coupon_status()
        if checked_coupon == OPENED_FISCAL_COUPON:
            self._cancel_fiscal_coupon()
        elif checked_coupon == OPENED_NON_FISCAL_COUPON:
            self._cancel_non_fiscal_coupon()

    def coupon_add_item(self, code, description, price, taxcode,
                        quantity=Decimal("1.0"), unit=UnitType.EMPTY,
                        discount=Decimal("0.0"), markup=Decimal("0.0"),
                        unit_desc=""):
        coupon_status = self._get_coupon_status()
        if coupon_status != OPENED_FISCAL_COUPON:
            raise CouponNotOpenError(_("Coupon is not open"))

        if unit == UnitType.CUSTOM:
            unit = unit_desc
        else:
            unit = self._consts.get_value(unit)
        qtd = int(quantity * self._decimals_quantity)
        value = int(price * self._decimals_price)
        st = taxcode
        # Register the sale item
        reply = self._send_command('0A02', '0000', code, description,
                                   str(qtd), unit, str(value), st)
        id = reply.fields[0]
        if discount:
            self.apply_discount(id, discount)
        elif markup:
            self.apply_markup(id, markup)
        return int(id)

    def apply_discount(self, id, discount):
        value = int(discount * Decimal('1e2'))
        # Register the discount on the item
        self._send_command('0A04', '0004', str(value))

    def apply_markup(self, id, markup):
        value = int(markup * Decimal('1e2'))
        # Register the markup on the item
        self._send_command('0A04', '0005', str(value))

    def coupon_cancel_item(self, item_id):
        self._send_command('0A18', '0004', str(item_id))

    def cancel_last_coupon(self):
        # Informações sobre último documento.
        reply = self._send_command('0908')
        last_coupon = reply.fields[0]
        if last_coupon == FISCAL_COUPON:
            self._cancel_fiscal_coupon()
        elif last_coupon == NON_FISCAL_COUPON:
            self._cancel_non_fiscal_coupon()
        else:
            raise DriverError(_("Attempt to cancel after emission of another "
                                "DOC"))

    def coupon_totalize(self, discount=currency(0), markup=currency(0),
                        taxcode=TaxType.NONE):
        if discount:
            extension = '0006'
            value = discount
        else:
            extension = '0007'
            value = markup

        # Podemos somente mandar o comando de desconto/acrescimo se realmente
        # tivermos um valor.
        if value:
            value = int(value * Decimal('1e2'))
            reply = self._send_command('0A04', extension, str(value))
            subtotal = reply.fields[0]
        else:
            # Ainda precisamos pegar o subtotal, para retornar.
            reply = self._send_command('0A03')
            subtotal = reply.fields[0]
        return currency(subtotal) / Decimal('1e2')

    def coupon_add_payment(self, payment_method, value, description=u""):
        desc = description[:40]
        value = int(value * Decimal('1e2'))
        reply = self._send_command('0A05', '0000', payment_method, str(value),
                                   desc, '')
        # Return the still missing value
        return currency(reply.fields[0]) / Decimal('1e2')

    def coupon_close(self, message=""):
        if self._customer_document:
            self._send_command('0A20', '0002', self._customer_document[:20],
                               self._customer_name[:30],
                               self._customer_address[:40],
                               self._customer_address[41:79])
            self._reset()

        if message:
            self._print_promotional_message(message)

        reply = self._send_command('0A06', '0001')
        self._send_command('0702', '0000')
        return int(reply.fields[0])

    def gerencial_report_open(self):
        return self._send_command('0E01', '0004', '1')

    def gerencial_report_print(self, text):
        self._print_report_text(text)

    def gerencial_report_close(self):
        self._send_command('0E06')

    def _print_report_text(self, text):
        """ Format the text according to limit of collumns number.
        """

        # Number of characters per line must be less than 56.
        for line in text.split('\n'):
            if line == '':
                self._print_line(line)
            for pos in range(0, len(line), 56):
                data = line[pos:pos + 56]
                self._print_line(data)

    def _print_line(self, line):
        """
        As seen on ACBr code.
        Remove char '\r'. When the ECF receives the character \r,
        the error, 020E(invalid attribute) is emitted.
        """
        line = line.strip('\r')
        self._send_command('0E02', '0000', line)

    def _print_promotional_message(self, message):
        msg = []
        # Epson accepts only 56 chars per line. Lets truncate each line
        for line in message.split('\n'):
            msg.append(line[:56])

        # We must send 8 lines to fiscal printer, even if they are empty.
        while len(msg) < 8:
            msg.append('')
        self._send_command('0A22', '0000', *msg[:8])

    #
    #   General information
    #

    def get_serial(self):
        reply = self._get_ecf_details()
        return reply.fields[0]

    def get_tax_constants(self):
        reply = self._send_command('0542')
        constants = []

        fields = reply.fields
        if len(fields) > 2:
            for i in range(0, len(fields), 3):
                name, value = fields[i], fields[i + 1]

                if name.startswith('T'):
                    type = TaxType.CUSTOM
                elif name.startswith('S'):
                    type = TaxType.SERVICE
                else:
                    assert False, (name, value)

                constants.append((type, name, Decimal(value) / 100))

        constants.extend([
            (TaxType.SUBSTITUTION, 'F', None),
            (TaxType.EXEMPTION, 'I', None),
            (TaxType.NONE, 'N', None),
        ])

        return constants

    def get_payment_constants(self):
        methods = []

        for i in range(20):
            try:
                reply = self._send_command('050D', '0000', '%d' % (i + 1))
            except DriverError, e:
                if e.code == 0x090C:  # Tipo de pagamento não definido
                    continue
                else:
                    raise
            name, vinculado = reply.fields
            methods.append(('%d' % (i + 1), name.strip()))

        return methods

    def get_capabilities(self):
        from stoqdrivers.printers.capabilities import Capability
        return dict(
            item_code=Capability(max_len=14),
            item_description=Capability(max_len=233),
            customer_id=Capability(max_len=28),
            customer_name=Capability(max_len=30),
            customer_address=Capability(max_len=79),
        )

    def get_constants(self):
        return self._consts

    def _get_ecf_details(self):
        return self._send_command('0402')

    def get_firmware_version(self):
        reply = self._get_ecf_details()
        return reply.fields[5]

    def get_coo(self):
        reply = self._send_command('0907')
        return int(reply.fields[0])

    def get_gnf(self):
        reply = self._send_command('0907')
        return int(reply.fields[3])

    def get_ccf(self):
        reply = self._send_command('0907')
        return int(reply.fields[7])

    def get_cro(self):
        reply = self._send_command('0907')
        return int(reply.fields[2])

    def get_crz(self):
        reply = self._send_command('0907')
        return int(reply.fields[1])

    def _get_taxes(self):
        reply = self._send_command('0542')
        tax_codes = reply.fields

        taxes = []
        for i in range(20):
            reg = tax_codes[i * 3:i * 3 + 3]
            if not reg:
                continue

            name = reg[0]
            if name.startswith('T'):
                tax_type = 'ICMS'
            else:
                tax_type = 'ISS'

            sold = reg[2]
            value = reg[1]
            taxes.append((value, self._parse_price(sold), tax_type))
        tax_totals = self._send_command('0906')

        taxes.append(('I', self._parse_price(tax_totals.fields[16]), 'ICMS'))
        taxes.append(('F', self._parse_price(tax_totals.fields[15]), 'ICMS'))
        taxes.append(('N', self._parse_price(tax_totals.fields[17]), 'ICMS'))
        taxes.append(('DESC', self._parse_price(tax_totals.fields[3]), 'ICMS'))
        taxes.append(('CANC', self._parse_price(tax_totals.fields[2]), 'ICMS'))

        return taxes

    #
    # Status
    #

    def _get_fiscal_status(self):
        reply = self._send_command('0001')
        return reply.check_fiscal_status()

    def _get_printer_status(self):
        reply = self._send_command('0001')
        return reply.check_printer_status()

    def _get_coupon_status(self):
        # Last four digits of fiscal status, show coupon status
        return self._get_fiscal_status()[12:16]

    #
    #   Printer configuration
    #

    def _define_payment_method(self, id, name, vinculated=False):
        if vinculated:
            extension = '0001'
        else:
            extension = '0000'

        id = '%02d' % id
        self._send_command('050C', extension, id, name)

    def _define_tax_code(self, value, service=False):
        if service:
            extension = '0001'
        else:
            extension = '0000'

        self._send_command('0540', extension, value)

    def _setup_constants(self):
        self._define_payment_method(2, 'Cheque')
        self._define_payment_method(3, 'Boleto')
        self._define_payment_method(4, 'Cartao credito', vinculated=True)
        self._define_payment_method(5, 'Cartao debito', vinculated=True)
        self._define_payment_method(6, 'Financeira')
        self._define_payment_method(7, 'Vale compra')

        self._define_tax_code("1700")
        self._define_tax_code("1200")
        self._define_tax_code("2500")
        self._define_tax_code("0800")
        self._define_tax_code("0500")
        self._define_tax_code("0300", service=True)
        self._define_tax_code("0900", service=True)


if __name__ == '__main__':
    from stoqdrivers.serialbase import SerialPort
    #port = Serial('/dev/pts/5')
    port = SerialPort('/dev/ttyUSB0')
    p = FBII(port)

#    p._send_command('0754', '0000') Desativar corte do papel

#    p._setup_constants()
#    constants = p.get_tax_constants()
#    for i in constants:
#        print i

#    constants = p.get_payment_constants()
#    for i in constants:
#        print i
