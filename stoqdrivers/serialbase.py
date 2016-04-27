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

from serial import Serial, EIGHTBITS, PARITY_NONE, STOPBITS_ONE
from zope.interface import implements

from stoqdrivers.interfaces import ISerialPort
from stoqdrivers.exceptions import DriverError
from stoqdrivers.translation import stoqdrivers_gettext

_ = stoqdrivers_gettext

log = logging.getLogger('stoqdrivers.serial')


class VirtualPort:
    implements(ISerialPort)

    def getDSR(self):
        return True

    def setDTR(self, value):
        pass

    def write(self, data):
        pass

    def read(self, n_bytes=1):
        return ''


class SerialPort(Serial):
    implements(ISerialPort)

    def __init__(self, device, baudrate=9600):
        # WARNING: Never change these default options, some drivers are based
        # on this to work. Maybe we should change this and make all the driver
        # specify its options, but right now I think that's ok, since these
        # options are common to most of the drivers.
        Serial.__init__(self, device, baudrate=baudrate, bytesize=EIGHTBITS,
                        parity=PARITY_NONE, stopbits=STOPBITS_ONE, timeout=3,
                        writeTimeout=0)
        self.setDTR(True)
        self.flushInput()
        self.flushOutput()


class SerialBase(object):

    # All commands will have this prefixed
    CMD_PREFIX = '\x1b'
    CMD_SUFFIX = ''

    # used by readline()
    EOL_DELIMIT = '\r'

    def __init__(self, port):
        self._port = port

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
        log.debug(">>> %r (%d bytes)" % (data, len(data)))
        self._port.write(data)

    def read(self, n_bytes):
        return self._port.read(n_bytes)

    def readline(self):
        out = ''
        a = 0
        retries = 10
        while True:
            if a > retries:
                raise DriverError(_("Timeout communicating with fiscal "
                                    "printer"))

            c = self._port.read(1)
            if not c:
                a += 1
                print 'take %s' % a
                continue
            a = 0
            if c == self.EOL_DELIMIT:
                log.debug('<<< %r' % out)
                return out
            out += c
