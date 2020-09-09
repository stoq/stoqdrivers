# -*- Mode: Python; coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

#
# Stoqdrivers
# Copyright (C) 2006 Async Open Source <http://www.async.com.br>
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
# Author(s):   Henrique Romano  <henrique@async.com.br>
#

from importlib import import_module

from zope.interface import implementer

from stoqdrivers.interfaces import IBarcodeReader
from stoqdrivers.serialbase import SerialBase


@implementer(IBarcodeReader)
class BaseBarcodeReader(SerialBase):
    # Should be defined in subclasses
    model_name = None

    def __init__(self, port, consts=None):
        SerialBase.__init__(self, port)

    def get_code(self):
        return self.readline()


def get_supported_barcode_readers():
    result = {}
    for brand, module_names in [('metrologic', ['MC630'])]:
        result[brand] = []
        for module_name in module_names:
            module = import_module("stoqdrivers.readers.barcode.%s.%s" % (brand, module_name))
            try:
                obj = getattr(module, module_name)
            except AttributeError:
                raise ImportError("Can't find class %s for module %s" % (module_name, module_name))
            if not IBarcodeReader.implementedBy(obj):
                raise TypeError("The driver %s %s doesn't implements a "
                                "valid interface" % (brand, obj.model_name))
            result[brand].append(obj)
    return result
