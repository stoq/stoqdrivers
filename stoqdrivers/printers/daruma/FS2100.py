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
## Author(s):   Henrique Romano <henrique@async.com.br>
##
"""
Daruma FS2100 driver
"""

import operator
from decimal import Decimal
import time

from stoqdrivers.printers.daruma.FS345 import FS345, CMD_GET_TAX_CODES
from stoqdrivers.enum import UnitType, TaxType
from stoqdrivers.exceptions import DriverError

from kiwi.log import Logger

log = Logger('stoqdrivers.daruma')

ENQ = 05
ACK = 06
LF  = 10
CR  = 13
ESC = 27
FS  = 28
GS  = 29
FF  = 255

CMD_ADD_ITEM = 201

class FS2100(FS345):
    model_name = "Daruma FS 2100"

    def coupon_add_item(self, code, description, price, taxcode,
                        quantity=Decimal("1.0"), unit=UnitType.EMPTY,
                        discount=Decimal("0.0"),
                        surcharge=Decimal("0.0"), unit_desc=""):
        if surcharge:
            d = 2
            E = surcharge
        else:
            d = 0
            E = discount

        E = int(E)
        price = price
        quantity = quantity

        # The minimum size of the description, when working with one line for
        # description; if 0, write in multiple lines, if necessary.
        desc_size = 0

        if unit != UnitType.CUSTOM:
            unit = self._consts.get_value(unit)
        else:
            unit = "%2s" % unit_desc[:2] # units must be 2 byte size strings

        # XXX: We need test correctly if the price's calcule is right (we
        # don't can do it right now since the manual isn't so clean).
        data = ('%02s' # Tributary situation
                '%07d' # Quantity
                '%08d' # Unitary price
                '%d'   # 0=Discount(%) 1=Discount($) 2=Surcharge(%) 3=Surcharge($)
                '%04d' # Discount/Surcharge value
                '%07d' # *Padding* (since we have discount/surcharge only in %)
                '%02d' # Description size
                '%14s' # Code
                '%3s'  # Unit of measure
                '%s'   # Product descriptio?!?
                '\xff' # EOF
                % (taxcode, int(quantity * Decimal('1e3')),
                   int(price * Decimal('1e2')), d,
                   int(E * Decimal('1e2')),
                   0, desc_size, code, unit, description[:233]))

        value = self.send_new_command('F', CMD_ADD_ITEM, data)
        return int(value[3:6])

    def send_command(self, command, extra=''):
        """As seen on ACBr code

        Nas Darumas com MFD, em algumas situações o ECF pode ficar
        temporariamente inoperantente, enquanto a compactação da MFD está
        sendo efetuada. Nessa situação, o ECF retorna os seguintes códigos
        de erro: 35 - Relogio Inoperante ou 99 (não documentado).

        Segundo o Suporte Técnico da Daruma, quando este problema ocorre,
        devemos aguardar até que ele consiga responder corretamente.

        Esta rotina irá tentar enviar o comando por 10 vezes. Caso ela
        recebe os erros 35 ou 99... ele aguarda 100 milisegundos e tenta um
        novo envio...
        """

        for t in range(10):
            try:
                retval = FS345.send_command(self, command, extra)
            except DriverError, e:
                if e.code == 99 or e.code == 35:
                    log.debug('FS2100 >>> Error 99. Sleeping for 0.1')
                    time.sleep(0.1)
                    continue

                raise
            break

        # After we have tried to send the command T times, we need to read
        # all the responses. This is really crap
        for i in range(t):
            reply = self._read_reply()
            log.debug('Ignoring reply: %r' % reply)

        return retval

    def _check_response(self, retcode, raw):
        # Compatible with the fs345/fs2100
        compatible_error = retcode[1:3]
        extended_error = retcode[3:6]
        warning_code = retcode[6:8]
        log.debug('FS2100 >>> Error %s - Extended: %s - Warning: %s' %
                    (compatible_error, extended_error, warning_code))
        if int(compatible_error):
            # Mimic FS345 error format
            error_code = ':E%s' % compatible_error
            self.handle_error(error_code, raw)

    def send_new_command(self, prefix, command, extra='', ignore_error=False):
        """ This method is used to send especific commands to model FS2100.
        Note that the main differences are the prefix (0x1c + 'F', since we
        will use a function of the FS2100 superset) and the checksum, that
        must be included in the end of all the functions of this superset.
        """
        data = chr(command) + extra

        log.debug('FS2100 >>> %r %d' % (data, len(data)))
        data = chr(FS) + prefix + data

        checksum = reduce(operator.xor, [ord(d) for d in data], 0)
        self.write(data + chr(checksum))

        retval = self.readline()
        # After the CR, there is still one byte for the checksum
        retval_checksum = self.read(1)

        if not ignore_error:
            self._check_response(retval, data)

        return retval[1:]

    def _get_compatibility_mode(self):
        return self.send_new_command('R', 200, '138')

    def get_tax_constants(self):
        tax_codes = self.send_command(CMD_GET_TAX_CODES)[1:]
        lower_case = 'abcdefghijklmnop'

        constants = []
        for i in range(14):
            reg = tax_codes[i*5]
            if reg in 'ABCDEFGHIJKLMNOP':
                tax_type = TaxType.CUSTOM
            elif reg in lower_case:
                tax_type = TaxType.SERVICE
            else:
                raise AssertionError(reg)
            value = tax_codes[i*5+1:i*5+5]
            if value == '////':
                continue
            constants.append((tax_type,
                              #'T' + reg.lower(),
                              '%02d' % (lower_case.index(reg.lower()) + 1),
                              Decimal(value.replace('.', '')) / 100))

        # These definitions can be found on Page 60
        constants.extend([
            (TaxType.SUBSTITUTION,   '17', None), # F1
            (TaxType.EXEMPTION,      '19', None), # I1
            (TaxType.NONE,           '21', None), # N1
            ])

        return constants

