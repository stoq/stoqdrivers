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

import usb

from stoqdrivers.exceptions import USBDriverError

# Based on python-escpos's escpos.printer.Usb:
#
# https://github.com/python-escpos/python-escpos/blob/master/src/escpos/printer.py


# FIXME This is a temporary solution due to legacy python-usb being supported
# on some Ubuntu versions, its behavior should mimic usb.core.find for the
# things we need
def usb_find(idVendor=None, idProduct=None, custom_match=None):
    """Returns a list of USB devices that matches some parameters

    @param idVendor: Will match the device by idVendor, should be provided
                     along with idVendor.
    @param idProduct: Will match the device by idProduct, should be provided
                      along with idProduct
    @param custom_match: Custom function to match a list of devices
    """
    # Generate a function that always return True if custom match is None
    if custom_match is None:
        custom_match = lambda d: True

    matches = []
    for bus in usb.busses():
        for device in bus.devices:
            # If the user has asked for a particular product with a particular
            # idVendor and idProduct, just return it
            if (idVendor and idProduct and device.idVendor == idVendor and
                device.idProduct == idProduct):
                return device
            if custom_match(device):
                matches.append(device)

    # If a single device was requested and it was not found, return None
    if idVendor and idProduct:
        return None

    return matches


class UsbBase(object):
    """Base class for a USB Printer"""

    def __init__(self, vendor_id, product_id, interface=0, in_ep=0x82,
                 out_ep=0x01, timeout=0, *args, **kwargs):
        super(UsbBase, self).__init__(*args, **kwargs)
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.interface = interface
        self.timeout = timeout
        self.in_ep = in_ep
        self.out_ep = out_ep
        self.open()

    def __del__(self):
        """Stop using any unnecessary resources upon destruction"""
        self.close()

    def open(self):
        self.device = usb_find(idVendor=self.vendor_id,
                               idProduct=self.product_id)
        if self.device is None:
            raise USBDriverError('USB Device not found using %s:%s' %
                                 (self.vendor_id, self.product_id))

        self.handler = self.device.open()
        try:
            # Detach the kernel driver for this interface so that we can use
            # I/O operations on the device
            self.handler.detachKernelDriver(self.interface)
        except usb.USBError:
            # If the kernel driver has already been detached, the method above
            # will most likely fail, this check can be made more accurately on
            # newer versions of PyUSB (as seen on the commented code below).
            pass

        # FIXME: Using legacy for now, below there is newer versions code
        # check_driver = None
        #
        # try:
        #     check_driver = self.device.is_kernel_driver_active(0)
        # except NotImplementedError:
        #     pass
        #
        # if check_driver is None or check_driver:
        #     try:
        #         self.device.detach_kernel_driver(0)
        #     except usb.USBError as e:
        #         if check_driver is not None:
        #             print("Could not detatch kernel driver: {0}".format(str(e)))
        # self.device.set_configuration()
        # self.device.reset()

    def close(self):
        """Release the USB interface"""
        # FIXME: Legacy pyusb should release the interface when the object is
        #        destroyed
        # if self.device:
        #     usb.util.dispose_resources(self.device)
        self.device = None
        self.handler = None

    def write(self, data):
        """Write any data to the USB printer

        :param data: Any data to be written
        :type data: bytes
        """
        self.handler.bulkWrite(self.out_ep, data, self.timeout)
