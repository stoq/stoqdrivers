# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2015 Async Open Source <http://www.async.com.br>
## All rights reserved
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU Lesser General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., or visit: http://www.gnu.org/.
##
## Author(s): Stoq Team <stoq-devel@async.com.br>
##

from stoqdrivers.printers.base import BasePrinter


class NonFiscalPrinter(BasePrinter):
    def __init__(self, brand=None, model=None, device=None, config_file=None,
                 *args, **kwargs):
        BasePrinter.__init__(self, brand=brand, model=model, device=device,
                             config_file=config_file, *args,
                             **kwargs)

    @property
    def max_characters(self):
        return self._driver.max_characters

    def centralize(self):
        self._driver.centralize()

    def descentralize(self):
        self._driver.descentralize()

    def set_bold(self):
        self._driver.set_bold()

    def unset_bold(self):
        self._driver.unset_bold()

    def print_line(self, data):
        self._driver.print_line(data)

    def print_inline(self, data):
        self._driver.print_inline(data)

    def print_barcode(self, barcode):
        self._driver.print_barcode(barcode)

    def print_qrcode(self, code):
        self._driver.print_qrcode(code)

    def cut_paper(self):
        self._driver.cut_paper()
