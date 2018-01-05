# -*- Mode: Python; coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Stoqdrivers
## Copyright (C) 2018 Stoq Tecnologia <http://stoq.link>
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

from zope.interface import implementer

from stoqdrivers.usbbase import UsbBase
from stoqdrivers.escpos import EscPosMixin
from stoqdrivers.interfaces import INonFiscalPrinter


@implementer(INonFiscalPrinter)
class TP650(UsbBase, EscPosMixin):

    out_ep = 0x02

    supported = True
    model_name = "Tanca TP650"

    # This is for normal printing. Condensed mode is 64
    max_characters = 48


if __name__ == '__main__':
    dev = TP650(vendor_id=0x0fe6, product_id=0x811e)
    dev.write('\n\n\nbegin\n\n\n')
    dev.unset_condensed()
    print(dev)
    dev.write('-' * dev.max_characters)
    dev.write('right aligned >'.rjust(48))
    dev.write('< left aligned'.ljust(48))
    dev.set_condensed()
    dev.write('right aligned >'.rjust(64))
    dev.write('< left aligned'.ljust(64))
    dev.unset_condensed()

    dev.centralize()
    dev.set_bold()
    dev.write('Bold Centralized text\n')

    dev.set_double_height()
    dev.write('Bold Double Height\n')

    dev.descentralize()
    dev.unset_bold()

    dev.write('Normal Double Height\n')
    dev.unset_double_height()

    dev.write('Back to normal text\n')

    dev.write('\n\n\n')

    dev.print_barcode('1234567890')
    dev.print_qrcode('https://www.stoq.com.br')
    dev.write('\n\n\n')
    dev.write('\n\n\nend\n\n\n')
