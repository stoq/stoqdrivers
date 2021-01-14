# -*- Mode: Python; coding: iso-8859-1 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Stoqdrivers
## Copyright (C) 2005,2006 Async Open Source <http://www.async.com.br>
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
## Author(s):   Johan Dahlin     <jdahlin@async.com.br>
##              Henrique Romano  <henrique@async.com.br>
##


import logging
import socket
from serial import Serial, EIGHTBITS, PARITY_NONE, STOPBITS_ONE
from zope.interface import implementer

from stoqdrivers.interfaces import ISerialPort
from stoqdrivers.exceptions import DriverError, PrinterError
from stoqdrivers.translation import stoqdrivers_gettext
from stoqdrivers.utils import str2bytes, bytes2str

_ = stoqdrivers_gettext

log = logging.getLogger('stoqdrivers.serial')


@implementer(ISerialPort)
class VirtualPort:

    def getDSR(self):
        return True

    def setDTR(self, value):
        pass

    def write(self, data):
        pass

    def read(self, n_bytes=1):
        return ''


@implementer(ISerialPort)
class SerialPort(Serial):

    def __init__(self, device, baudrate=9600):
        # WARNING: Never change these default options, some drivers are based
        # on this to work. Maybe we should change this and make all the driver
        # specify its options, but right now I think that's ok, since these
        # options are common to most of the drivers.
        Serial.__init__(self, device, baudrate=baudrate, bytesize=EIGHTBITS,
                        parity=PARITY_NONE, stopbits=STOPBITS_ONE, timeout=3,
                        write_timeout=3)
        self.setDTR(True)
        self.flushInput()
        self.flushOutput()


# When we are printing NFCe danfe there is a hack that forces the reinitialization of the printer.
# So this variable is used to check if we need to create a new socket or reuse the previous one.
active_device = None


class EthernetPort:
    def __init__(self, address, port):
        self.address = address
        self.port = port
        self._get_or_create_connection()

    def _get_or_create_connection(self):
        self.device = active_device or self._create_connection()

    def _create_connection(self):
        global active_device
        try:
            active_device = self.device = socket.create_connection(
                (self.address, self.port), timeout=5)
        except OSError:
            raise PrinterError

    def _check_device(self):
        # The device can be None if flask starts without a printer on,
        # when the printer is turned on, the stoqserver can reset
        # the connection with the socket.
        if not isinstance(self.device, socket.socket):
            raise PrinterError

    def write(self, data):
        self._check_device()
        try:
            self.device.sendall(data)
        except (ConnectionResetError, OSError):
            self._create_connection()
            self.device.sendall(data)

    def read(self, n_bytes):
        self._check_device()
        try:
            data = self.device.recv(n_bytes)
        except (ConnectionResetError, socket.timeout):
            raise PrinterError

        return str2bytes(data)

    def flush(self):
        self._check_device()
        f = self.device.makefile()
        f.flush()

    def open(self):
        if not self.is_open():
            try:
                self.device.connect((self.address, self.port))
            except OSError:
                raise PrinterError

    def close(self):
        if self.is_open():
            self.device.close()

    def is_open(self):
        self._check_device()
        return not self.device.closed


class SerialBase(object):

    # All commands will have this prefixed
    CMD_PREFIX = '\x1b'
    CMD_SUFFIX = ''

    # used by readline()
    EOL_DELIMIT = '\r'

    # Most serial printers allow connecting a cash drawer to them. You can then
    # open the drawer, and also check its status. Some models, for instance,
    # the Radiant drawers, use inverted logic to describe whether they are
    # open, specified by this attribute, settable via BaseDevice config.
    inverted_drawer = False

    def __init__(self, port):
        self.set_port(port)

    def set_port(self, port):
        self._port = port

    def get_port(self):
        return self._port

    def fileno(self):
        return self._port.fileno()

    def writeline(self, data):
        self.write(self.CMD_PREFIX + data + self.CMD_SUFFIX)
        return self.readline()

    def write(self, data):
        # pyserial is expecting bytes but we work with str in stoqdrivers
        data = str2bytes(data)
        log.debug(">>> %r (%d bytes)" % (data, len(data)))
        self._port.write(data)

    def read(self, n_bytes):
        # stoqdrivers is expecting str but pyserial will reply with bytes
        data = self._port.read(n_bytes)
        return bytes2str(data)

    def readline(self):
        out = ''
        a = 0
        retries = 10
        while True:
            if a > retries:
                raise DriverError(_("Timeout communicating with fiscal "
                                    "printer"))

            c = self.read(1)
            if not c:
                a += 1
                print('take %s' % a)
                continue
            a = 0
            if c == self.EOL_DELIMIT:
                log.debug('<<< %r' % out)
                return out
            out += c

    def open(self):
        if not self._port.is_open:
            self._port.open()

    def close(self):
        if self._port.is_open:
            # Flush whaterver is pending to write, since port.close() will close it
            # *imediatally*, losing what was pending to write.
            self._port.flush()
            self._port.close()
