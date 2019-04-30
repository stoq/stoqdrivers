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

import re

from stoqdrivers.printers.base import BasePrinter


class NonFiscalPrinter(BasePrinter):
    def __init__(self, brand=None, model=None, device=None, config_file=None,
                 *args, **kwargs):
        BasePrinter.__init__(self, brand, model, device, config_file, *args,
                             **kwargs)

    @property
    def charset(self):
        # The driver might not have defined a charset, or it might be None
        return getattr(self._driver, 'charset', 'utf8') or 'utf8'

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

    def set_condensed(self):
        self._driver.set_condensed()

    def unset_condensed(self):
        self._driver.unset_condensed()

    def set_double_height(self):
        self._driver.set_double_height()

    def unset_double_height(self):
        self._driver.unset_double_height()

    def print_line(self, data):
        if isinstance(data, str):
            data = data.encode(self.charset)
        self.print_inline(data + b'\n')

    def print_inline(self, data):
        if isinstance(data, str):
            data = data.encode(self.charset)
        start = 0
        for tag in re.finditer(b'<\w+>', data):
            # Text before the tag
            text = data[start: tag.start()]
            if text:
                self._driver.print_inline(text)
            start = tag.end()

            tag = tag.group()[1:-1].decode()  # remove < and >
            if hasattr(self, tag):
                getattr(self, tag)()

        # any remaining text after the last tag
        text = data[start:]
        if text:
            self._driver.print_inline(text)

    def print_barcode(self, barcode):
        self._driver.print_barcode(barcode)

    def print_qrcode(self, code):
        self._driver.print_qrcode(code)

    def print_matrix(self, data):
        if hasattr(self._driver, 'print_matrix'):
            self._driver.print_matrix(data)

    def separator(self):
        if hasattr(self._driver, 'separator'):
            self._driver.separator()
        else:
            self._driver.print_line(b'-' * self.max_characters)

    def cut_paper(self):
        self._driver.cut_paper()

    def open_drawer(self):
        if hasattr(self._driver, 'open_drawer'):
            self._driver.open_drawer()

    def is_drawer_open(self):
        if hasattr(self._driver, 'is_drawer_open'):
            return self._driver.is_drawer_open()
        else:
            return False

    def open(self):
        if hasattr(self._driver, 'open'):
            self._driver.open()

    def close(self):
        if hasattr(self._driver, 'close'):
            self._driver.close()
