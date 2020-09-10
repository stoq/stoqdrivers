# -*- Mode: Python; coding: iso-8859-1 -*-
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
# Author(s): Henrique Romano             <henrique@async.com.br>
#
"""
Generic base class implementation for all devices.
"""

import logging
from unittest import mock

try:
    from gi.repository import GObject
except ImportError:
    GObject = mock.Mock()

from stoqdrivers.configparser import StoqdriversConfig
from stoqdrivers.enum import DeviceType
from stoqdrivers.exceptions import CriticalError, ConfigError
from stoqdrivers.translation import stoqdrivers_gettext
from stoqdrivers.serialbase import SerialPort

_ = stoqdrivers_gettext

log = logging.getLogger('stoqdrivers.basedev')


class BaseDevice:
    """ Base class for all device interfaces, responsible for instantiate
    the device driver itself based on the brand and model specified or in
    the configuration file.
    """
    typename_translate_dict = {
        DeviceType.PRINTER: "Printer",
        DeviceType.SCALE: "Scale",
        DeviceType.BARCODE_READER: "Barcode Reader",
    }
    # Subclasses must define these attributes
    device_dirname = None
    required_interfaces = None
    device_type = None

    INTERFACE_SERIAL = 'serial'
    INTERFACE_USB = 'usb'
    INTERFACE_ETHERNET = 'ethernet'

    def __init__(self, brand=None, model=None, device=None,
                 config_file=None, port=None, consts=None, product_id=None,
                 vendor_id=None, interface=INTERFACE_SERIAL, baudrate=9600,
                 inverted_drawer=None):
        if not self.device_dirname:
            raise ValueError("Subclasses must define the "
                             "`device_dirname' attribute")
        elif self.device_type is None:
            raise ValueError("device_type must be defined")
        self.interface = interface
        self.brand = brand
        self.device = device
        self.model = model
        self.inverted_drawer = inverted_drawer
        self.product_id = product_id
        self.vendor_id = vendor_id
        self._baudrate = baudrate
        self._port = port
        self._driver_constants = consts
        self._load_configuration(config_file)

    def _load_configuration(self, config_file):
        try:
            self.config = StoqdriversConfig(config_file)
        except ConfigError as e:
            log.info(e)
            self.config = None
        else:
            # This allows overriding in the config file some or all of the
            # data that was specified through the constructor
            section_name = BaseDevice.typename_translate_dict[self.device_type]
            for field in ['brand', 'device', 'model', 'inverted_drawer']:
                try:
                    setattr(self, field, self.config.get_option(field, section_name))
                except ConfigError:
                    # Field not found, ignore
                    pass

        # At this point, either we have the data needed to initialize the
        # device or we will need to bail
        if (not self.model or not self.brand or
            (self.interface == BaseDevice.INTERFACE_SERIAL and
             not self.device and not self._port)):
            raise ConfigError("Device not specified in config or constructor, giving up")

        name = "stoqdrivers.%s.%s.%s" % (self.device_dirname,
                                         self.brand, self.model)
        try:
            module = __import__(name, None, None, 'stoqdevices')
        except ImportError as reason:
            raise CriticalError("Could not load driver %s %s: %s"
                                % (self.brand.capitalize(),
                                   self.model.upper(), reason))
        class_name = self.model
        driver_class = getattr(module, class_name, None)
        if not driver_class:
            raise CriticalError("Device driver at %s needs a class called %s"
                                % (name, class_name))

        if self.interface == 'serial':
            if not self._port:
                self._port = SerialPort(self.device, self._baudrate)
            self._driver = driver_class(self._port, consts=self._driver_constants)
        elif self.interface == 'usb':
            self._driver = driver_class(self.vendor_id, self.product_id)
        else:
            raise NotImplementedError('Interface not implemented')

        log.info("Device class initialized: brand=%s,device=%s,model=%s"
                 % (self.brand, self.device, self.model))

        # This check is necessary but ugly because the configuration code
        # doesn't understand booleans, and we don't want mismatches
        if self.inverted_drawer in ("True", True):
            log.info("Inverting drawer check logic")
            self._driver.inverted_drawer = True

        self.check_interfaces()

    def get_model_name(self):
        return self._driver.model_name

    def get_firmware_version(self):
        """Printer firmware version
        """
        return self._driver.get_firmware_version()

    def check_interfaces(self):
        """ This method must be implemented in subclass and must ensure that the
        driver implements a valid interface for the current operation state.
        """
        raise NotImplementedError

    def notify_read(self, func):
        """ This function can be called when the callsite must know when data
        is coming from the serial port.   It is necessary that a gobject main
        loop is already running before calling this method.
        """
        GObject.io_add_watch(self.get_port().fd, GObject.IO_IN, lambda fd, cond: func(self, cond))

    def set_port(self, port):
        self._driver.set_port(port)

    def get_port(self):
        return self._driver.get_port()
