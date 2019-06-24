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
## Author(s):   Christian Reis         <kiko@async.com.br>
##

from stoqdrivers.printers.nonfiscal import NonFiscalPrinter
from stoqdrivers.configparser import StoqdriversConfig

from tests.base import _BaseTest

from PIL import Image

# Patch StoqdriversConfig to look for config files in tests/
StoqdriversConfig.get_homepath = lambda self: "tests/"


class _TestNonFiscalPrinter(object):
    """ Test nonfiscal printing"""
    device_class = NonFiscalPrinter

    def test_init_conditions(self):
        self._device.print_line('Init: Condensed and descentralized')

    def test_print(self):
        self._device.print_line('Print line')

    def test_print_inline(self):
        self._device.print_inline('Print ')
        self._device.print_line('inline')

    def test_centralize(self):
        self._device.centralize()
        self._device.print_line('Centralized')
        self._device.descentralize()
        self._device.print_line('Descentralized')

    def test_bold(self):
        self._device.set_bold()
        self._device.print_inline('Bold')
        self._device.unset_bold()
        self._device.print_line(' Normal')

    def test_condensed(self):
        self._device.unset_condensed()
        self._device.print_inline('Uncondensed')
        self._device.set_condensed()
        self._device.print_line(' Normal')

    def test_double_height(self):
        self._device.set_double_height()
        self._device.print_inline('Double Height')
        self._device.unset_double_height()
        self._device.print_line(' Normal')

    def test_barcode(self):
        self._device.print_barcode('123456789')

    def test_qrcode(self):
        self._device.print_qrcode('This is a qr code')

    def test_print_image(self):
        im = Image.open("tests/data/image.png")
        data = []
        for y in range(im.height):
            row = []
            for x in range(im.width):
                row.append(im.getpixel((x, y)) == 0)

            data.append(row)

        self._device.print_matrix(data)

    def test_cut(self):
        self._device.cut_paper()


class _NonFiscalWithDrawerSupport(_TestNonFiscalPrinter, _BaseTest):
    def test_init(self):
        pass

    def test_open_drawer(self):
        self._device.open_drawer()

    def test_check_drawer(self):
        # The data files we are reading return 0x04 for the return value of the
        # raw command. In the normal (i.e. not inverted_drawer) case, this
        # indicates the drawer is closed.
        self.assertEquals(self._device.is_drawer_open(), False)


class BematechMP2100TH(_NonFiscalWithDrawerSupport):
    brand = 'bematech'
    model = 'MP2100TH'


class ElginI9(_NonFiscalWithDrawerSupport):
    brand = 'elgin'
    model = 'I9'


class SwedaSI300(_NonFiscalWithDrawerSupport):
    brand = 'sweda'
    model = 'SI300'


class BematechMP2100TH_InvertedDrawer(_NonFiscalWithDrawerSupport):
    brand = 'bematech'
    model = 'MP2100TH'

    def get_device_init_kwargs(self):
        return {'config_file': "stoqdrivers-inverteddrawer.conf"}

    def test_check_drawer(self):
        self.assertEquals(self._device.is_drawer_open(), True)


class ElginI9_InvertedDrawer(_NonFiscalWithDrawerSupport):
    brand = 'elgin'
    model = 'I9'

    def get_device_init_kwargs(self):
        return {'config_file': "stoqdrivers-inverteddrawer.conf"}

    def test_check_drawer(self):
        self.assertEquals(self._device.is_drawer_open(), True)
