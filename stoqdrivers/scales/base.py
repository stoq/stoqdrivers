# -*- Mode: Python; coding: iso-8859-1 -*-
# vi:si:et:sw=4:sts=4:ts=4

#
# Stoqdrivers
# Copyright (C) 2005 Async Open Source <http://www.async.com.br>
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
# Author(s): Henrique Romano             <henrique@async.com.br>
#
"""
Useful functions related to all scales supported by stoqdrivers
"""

from zope.interface import providedBy

from stoqdrivers.base import BaseDevice
from stoqdrivers.enum import DeviceType
from stoqdrivers.interfaces import IScale
from stoqdrivers.utils import get_obj_from_module


class BaseScale(BaseDevice):
    device_dirname = "scales"
    device_type = DeviceType.SCALE

    def check_interfaces(self):
        driver_interfaces = providedBy(self._driver)
        if IScale not in driver_interfaces:
            raise TypeError("This driver doesn't implements a valid interface")


def get_supported_scales():
    result = {}

    for brand, module_names in [
        (u'toledo', [u'PrixIII']),
        (u'micheletti', [u'MicP15'])
    ]:
        result[brand] = []
        for module_name in module_names:
            full_module_name = "stoqdrivers.scales.%s.%s" % (brand, module_name)
            obj = get_obj_from_module(full_module_name, obj_name=module_name)
            if not IScale.implementedBy(obj):
                raise TypeError("The driver %s %s doesn't implements a "
                                "valid interface"
                                % (brand, obj.model_name))
            result[brand].append(obj)
    return result
