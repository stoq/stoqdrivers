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

from tests.base import _BaseTest


class _TestNonFiscalPrinter(object):
    """ Test nonfiscal printing"""
    device_class = NonFiscalPrinter


class _NonFiscalWithDrawerSupport(_TestNonFiscalPrinter, _BaseTest):
    def test_init(self):
        pass

    def test_open_drawer(self):
        self._device.open_drawer()

    def test_check_drawer(self):
        self._device.is_drawer_open()


class BematechMP2100TH(_NonFiscalWithDrawerSupport, _BaseTest):
    brand = 'bematech'
    model = 'MP2100TH'


class ElginI9(_NonFiscalWithDrawerSupport, _BaseTest):
    brand = 'elgin'
    model = 'I9'
