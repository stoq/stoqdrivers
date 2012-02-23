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
## Author(s): Stoq Team <stoq-devel@async.com.br>
##
"""
Epson FB II ECF driver
"""

#import datetime
#import time
import struct
from decimal import Decimal
from kiwi.datatypes import currency

from zope.interface import implements

from stoqdrivers.serialbase import SerialBase
from stoqdrivers.interfaces import ICouponPrinter
from stoqdrivers.exceptions import DriverError
#from stoqdrivers.exceptions import (DriverError, PendingReduceZ, PendingReadX,
#                                    PrinterError, CommError, CommandError,
#                                    CommandParametersError, ReduceZError,
#                                    HardwareFailure, OutofPaperError,
#                                    CouponNotOpenError, CancelItemError,
#                                    CouponOpenError)
from stoqdrivers.enum import TaxType, UnitType
#from stoqdrivers.printers.capabilities import Capability
#from stoqdrivers.printers.base import BaseDriverConstants
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
        string = string.replace(i, ESC+i)
    return string

def unescape(string):
    for i in SPECIAL_CHARS:
        string = string.replace(ESC+i, i)
    return string


_ = stoqdrivers_gettext

class Reply(object):

    #
    #   Printer flags
    #

    def __init__(self, string, command_id):
        checksum = string[-4:]
        self.string = string[:-4]

        #print 'reply', repr(string)
        cs = '%04X' % sum([ord(i) for i in self.string])
        assert cs == checksum, 'checksum'

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
        # FIXME: Verificar erros
        if self.reply_status != '0000':
            print 'reply_status', self.reply_status
            raise DriverError('')

    def pop(self, size=1):
        """Remove size bites from the begining of self.string and returns it
        """
        head = self.string[:size]
        self.string = self.string[size:]
        return head

    def check_printer_status(self):
        pass

    def check_fiscal_status(self):
        pass


#
# The driver implementation
#

class FBII(SerialBase):

    implements(ICouponPrinter)

    supported = True
    identify_customer_at_end = True

    model_name = "FBII"
    cheque_printer_charset = "ascii"
    coupon_printer_charset = "ascii"

    def __init__(self, port, consts=None):
        SerialBase.__init__(self, port)
        self._command_id = 128 #0x80

    #
    # Helper methods
    #

    def _get_next_command_id(self):
        self._command_id += 1
        # FIXME: Loop
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
        package = STX +  command_id + frame + ETX

        checksum = sum([ord(d) for d in package])
        return package + '%04X' % checksum

    def _read_reply(self):
        reply = ''
        while True:
            c = self.read(1)
            reply += c

            if c == ETX and reply[-2] != ESC:
                break

        reply += self.read(4)
        print '< ', repr(reply)

        return Reply(reply, self._command_id)

    def _send_command(self, command, extension='0000', *args):
        cmd = self._get_package(command, extension, args)
        print '> ', repr(cmd)
        self.write(cmd)

        # Printer should reply with an ACK imediataly
        ack = self.read(1)
        assert ack == ACK, repr(ack)

        reply = self._read_reply()

        # Keep reading while printer sends intermediate replies.
        while reply.intermediate:
            print 'intermediate'
            reply = self._read_reply()

        # send our ACK
        self.write(ACK)

        reply.check_error()
        return reply

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

    def close_till(self, previous_day=False):
        # Nesse momento é possível realizar ajustes no horário da ECF (como
        # entrar e sair do horário de verão. Podemos estudar implementar isso no
        # stoq.
        self._send_command('0801', '0000', '', '')

    def _add_voucher(self, type, value):
        # Abre comprovante não fiscal
        self._send_command('0E01', '0000', '')

        # Adiciona item
        value = '%d' % (value * 100)
        self._send_command('0E15', '0000', type, value)

        # Fecha
        self._send_command('0E06')

    def till_add_cash(self, value):
        self._add_voucher('02', value)

    def till_remove_cash(self, value):
        self._add_voucher('01', value)

    def get_sintegra(self):
        return None


    #
    # Coupon related commands
    #

    def coupon_open(self):
        self._send_command('0A01', '0000', '', '')

    def coupon_cancel(self):
        self._send_command('0A18', '0008', '1')

    def coupon_add_item(self, code, description, price, taxcode,
                        quantity=Decimal("1.0"), unit=UnitType.EMPTY,
                        discount=Decimal("0.0"), markup=Decimal("0.0"),
                        unit_desc=""):
        # FIXME
        qtd = '%d' % (quantity * 1000)
        un = 'UN'
        value = '%d' % (price * 100)
        st = taxcode
        reply = self._send_command('0A02', '0000', code, description, qtd, un, value, st)
        # FIXME: return id of added item
        id = reply.fields[0]
        print 'XXX', id
        return int(id)

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
            value = '%d' % (value * 100)
            reply = self._send_command('0A04', extension, value)
            subtotal = reply.fields[0]
        else:
            # Ainda precisamos pegar o subtotal, para retornar.
            reply = self._send_command('0A03')
            subtotal = reply.fields[0]
        return currency(subtotal) / Decimal('1e2')

    def coupon_add_payment(self, payment_method, value, description=u""):
        desc = description[:40]
        value = '%d' % (value * 100)
        reply = self._send_command('0A05', '0000', payment_method, value, desc,
                                    '')
        # Return the still missing value
        return currency(reply.fields[0]) / Decimal('1e2')

    def coupon_close(self, message=""):
        reply = self._send_command('0A06', '0000')
        return int(reply.fields[0])

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
                name, value = fields[i], fields[i+1]

                if name.startswith('T'):
                    type = TaxType.CUSTOM
                elif name.startswith('S'):
                    type = TaxType.SERVICE
                else:
                    assert False, (name, value)

                constants.append((type, name, Decimal(value) / 100))

        constants.extend([
            (TaxType.SUBSTITUTION, 'F', None),
            (TaxType.EXEMPTION,    'I', None),
            (TaxType.NONE,         'N', None),
            ])

        return constants

    def get_payment_constants(self):
        methods = []

        for i in range(20):
            try:
                reply = self._send_command('050D', '0000', '%d' % (i+1))
            except DriverError:
                # TODO:
                #if reply.reply_status == '090C':
                break
            name, vinculado = reply.fields
            methods.append(('%d' % (i+1), name.strip()))

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

    def _get_ecf_details(self):
        return self._send_command('0402')

    def has_pending_reduce(self):
        #FIXME
        return False

    def get_coo(self):
        reply = self._send_command('0907')
        return int(reply.fields[0])

    def get_gnf(self):
        reply = self._send_command('0907')
        return int(reply.fields[3])

    def get_ccf(self):
        reply = self._send_command('0907')
        return int(reply.fields[7])

    def get_crz(self):
        reply = self._send_command('0907')
        return int(reply.fields[1])

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
        return



if __name__ == '__main__':
    from serial import Serial
    #port = Serial('/dev/pts/5')
    port = Serial('/tmp/fpii')
    p  = FBII(port)
    #p.summarize()
    print p.get_serial()
    print
    #p._setup_constants()
    constants = p.get_tax_constants()
    for i in constants:
        print i

    constants = p.get_payment_constants()
    for i in constants:
        print i
