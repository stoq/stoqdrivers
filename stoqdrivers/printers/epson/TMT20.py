# -*- Mode: Python; coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Stoqdrivers
## Copyright (C) 2016 Stoq Tecnologia <http://stoq.link>
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
from zope.interface import implements

from stoqdrivers.usbbase import UsbBase
from stoqdrivers.escpos import EscPosMixin
from stoqdrivers.interfaces import INonFiscalPrinter


class TMT20(UsbBase, EscPosMixin):
    implements(INonFiscalPrinter)

    supported = True
    model_name = "Epson TM-T20"
