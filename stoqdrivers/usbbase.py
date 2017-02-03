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
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
## USA.

try:
    import usb.core
    import usb.util
    has_usb = True
except ImportError:
    has_usb = False

from stoqdrivers.exceptions import USBDriverError

# Based on python-escpos's escpos.printer.Usb:
#
# https://github.com/python-escpos/python-escpos/blob/master/src/escpos/printer.py


class UsbBase(object):
    """Base class for a USB Printer"""

    #: Out Endpoint address. Subclasses must define this.
    out_ep = None

    def __init__(self, vendor_id, product_id, interface=0,
                 timeout=0, *args, **kwargs):
        assert has_usb
        super(UsbBase, self).__init__(*args, **kwargs)
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.interface = interface
        self.timeout = timeout
        assert self.out_ep is not None

    def __del__(self):
        """Stop using any unnecessary resources upon destruction"""
        self.close()

    def open(self):
        self.device = usb.core.find(idVendor=self.vendor_id,
                                    idProduct=self.product_id)
        if self.device is None:
            raise USBDriverError('USB Device not found using %s:%s' %
                                 (self.vendor_id, self.product_id))

        check_driver = None
        try:
            check_driver = self.device.is_kernel_driver_active(0)
        except NotImplementedError:
            pass

        if check_driver is None or check_driver:
            try:
                self.device.detach_kernel_driver(0)
            except usb.core.USBError as e:
                if check_driver is not None:
                    print("Could not detatch kernel driver: {0}".format(str(e)))

        self.device.set_configuration()
        self.device.reset()

    def close(self):
        """Release the USB interface"""
        if self.device:
            usb.util.dispose_resources(self.device)
        self.device = None

    def write(self, data):
        """Write any data to the USB printer

        :param data: Any data to be written
        :type data: bytes
        """
        self.device.write(self.out_ep, data, self.timeout)
