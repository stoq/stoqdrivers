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
## Author(s): Henrique Romano             <henrique@async.com.br>
##
"""
Generic base class implementation for all printers
"""

from zope.interface import providedBy, implements
from kiwi.python import namedAny

from stoqdrivers.interfaces import (ICouponPrinter,
                                    IDriverConstants,
                                    IChequePrinter,
                                    INonFiscalPrinter)
from stoqdrivers.base import BaseDevice
from stoqdrivers.serialbase import SerialBase
from stoqdrivers.usbbase import UsbBase
from stoqdrivers.enum import DeviceType
from stoqdrivers.translation import stoqdrivers_gettext

_ = stoqdrivers_gettext

_NoDefault = object()


class BaseDriverConstants:
    implements(IDriverConstants)

    # Must be defined on subclasses
    _constants = None

    @classmethod
    def get_items(cls):
        return cls._constants.keys()

    @classmethod
    def get_value(cls, identifier, default=_NoDefault):
        try:
            return cls._constants[identifier]
        except KeyError:
            if default is not _NoDefault:
                return default
            raise ValueError("The constant identifier %r "
                             "isn't valid", identifier)


class BasePrinter(BaseDevice):
    device_dirname = "printers"
    device_type = DeviceType.PRINTER

    def check_interfaces(self):
        driver_interfaces = providedBy(self._driver)
        if (not ICouponPrinter in driver_interfaces
                and not IChequePrinter in driver_interfaces
                and not INonFiscalPrinter in driver_interfaces):
            raise TypeError("The driver `%r' doesn't implements a valid "
                            "interface" % self._driver)

    def get_constants(self):
        return self._driver.get_constants()

    def get_tax_constant(self, item):
        for enum, constant, value in self.get_tax_constants():
            if enum == item:
                return constant

    def get_model_name(self):
        return self._driver.model_name


def get_virtual_printer():
    from stoqdrivers.printers.fiscal import FiscalPrinter
    return FiscalPrinter(brand='virtual', model='Simple')


def get_supported_printers(include_virtual=False):
    result = {}
    config = [
        ('bematech', ['DP20C', 'MP20', 'MP2100', 'MP2100TH', 'MP4200TH', 'MP25']),
        ('daruma', ['DR700', 'FS2100', 'FS345', 'FS600MFD']),
        ('dataregis', ['EP375', 'Quick']),
        ('elgin', ['I9', 'KFiscal']),
        ('epson', ['FBII', 'FBIII', 'TMT20']),
        ('fiscnet', ['FiscNetECF']),
        ('perto', ['Pay2023']),
        ('sweda', ['SI150']),
    ]
    if include_virtual:
        config.append(('virtual', ['Simple']))

    for brand, module_names in config:
        result[brand] = []
        for module_name in module_names:
            try:
                obj = namedAny("stoqdrivers.printers.%s.%s.%s"
                               % (brand, module_name, module_name))
            except AttributeError:
                raise ImportError("Can't find class %s for module %s"
                                  % (module_name, module_name))
            if not hasattr(obj, 'supported'):
                continue
            result[brand].append(obj)
    return result


def get_supported_printers_by_iface(interface, protocol=None,
                                    include_virtual=False):
    """ Returns all the printers that supports the interface.  The result
    format is the same for get_supported_printers.

    @param interface: The interface the printer implements
                      (ICouponPrinter, IChequePrinter or INonFiscalPrinter)
    @param protocol: The protocol in which the printer is connected
                     (None (all protocols), usb, serial or ethernet)
    @param include_virtual: If the virtual printer (for development) should be
                            included in the results
    """
    # Select the base class depending on which interface has been chosen
    # TODO: Implement Ethernet interface support
    base_class = {
        'usb': UsbBase,
        'serial': SerialBase,
        'ethernet': None,
        None: object,
    }[protocol]

    if not interface in (ICouponPrinter, IChequePrinter, INonFiscalPrinter):
        raise TypeError("Interface specified (`%r') is not a valid "
                        "printer interface" % interface)
    all_printers_supported = get_supported_printers(include_virtual=include_virtual)
    result = {}
    for model, driver_list in all_printers_supported.items():
        drivers = []
        for driver in driver_list:
            if interface.implementedBy(driver) and issubclass(driver, base_class):
                drivers.append(driver)
        if drivers:
            result[model] = drivers

    return result


def get_usb_printer_devices():
    """ List all printers connected via USB """
    try:
        import usb.core
    except ImportError:
        # No pyusb > 1.0.0 support, return an empty list
        return []

    def is_printer(device):
        """ Tests whether a device is a printer or not """
        # Devices with either bDeviceClass == 7 or bInterfaceClass == 7 are
        # printers
        if device.bDeviceClass == 7:
            return True
        for configuration in device:
            for interface in configuration:
                if interface.bInterfaceClass == 7:
                    return True
        return False
    return list(usb.core.find(find_all=True, custom_match=is_printer))


def get_baudrate_values():
    """ Returns baudrate values to configure the communication speed with
    serial port.
    """
    return ['4800', '9600', '19200', '38400', '57600', '115200']
