# -*- Mode: Python; coding: utf-8 -*-
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
# Author(s):    Henrique Romano  <henrique@async.com.br>
#               Johan Dahlin     <jdahlin@async.com.br>
#

from configparser import ConfigParser
import datetime
from numbers import Real
from typing import Optional

import pkg_resources
from zope.interface.exceptions import DoesNotImplement
from zope.interface import providedBy

from stoqdrivers.interfaces import IChequePrinter
from stoqdrivers.exceptions import ConfigError
from stoqdrivers.printers.base import BasePrinter
from stoqdrivers.utils import encode_text
from stoqdrivers.translation import stoqdrivers_gettext

_ = stoqdrivers_gettext


class BankConfiguration:
    """ This class store and manage the Cheque elements positions for a bank.
    """
    def __init__(self, name: str, items: dict):
        """ Create a new cheque configuration for the bank 'name'

        @param name:   The name of bank to which this configuration belongs to.
        @type name:    str
        @param items:  A dictionary where the key is the configuration name
                       and its values are the row and column coordinates,
                       respectively, eg: row['legal_amount1'] = (Y, X)
        @type items:   dict
        """
        self.name, self._items = name, items

    def get_coordinate(self, name: str):
        if name not in self._items:
            raise KeyError(name)
        return self._items[name]

    def get_x_coordinate(self, name: str):
        return self.get_coordinate(name)[1]

    def get_y_coordinate(self, name: str):
        return self.get_coordinate(name)[0]


class BaseChequePrinter:
    """ A base class for all printers that implements IChequePrinter interface.
    This class knows how to deal with the configuration file, that contains
    all the configuration of all supported cheques by the printer.

    @cvar CHEQUE_CONFIGFILE: This constant must be redefined in subclass and
                             must specify the filename where the cheque printer
                             configuration can be found.
    """
    CHEQUE_CONFIGFILE = None

    def __init__(self):
        self._banks = {}

    def get_banks(self):
        configfile = self.__module__.split('.')[-2] + '.ini'

        config = ConfigParser()
        resource_name = 'conf/%s' % configfile
        filename = pkg_resources.resource_filename('stoqdrivers', resource_name)
        if not config.read(filename):
            return None
        for section in config.sections():
            # With this, we'll have a dictionary in this format:
            # CONFIG_NAME: "Y,X"
            items = dict(config.items(section))
            try:
                bank = self._parse_bank(items)
            except ConfigError as errmsg:
                raise ConfigError("In section `%s' of `%s': %s"
                                  % (section, filename, errmsg))
            self._banks[int(section)] = bank
        return self._banks

    def _parse_bank(self, items: dict):
        if 'name' not in items:
            raise ConfigError("There is no bank name defined")
        coordinates = {}
        bank_name = items.pop('name')
        for name in ('value', 'legal_amount', 'legal_amount2', 'city',
                     'thirdparty', 'year', 'day', 'month'):
            if name not in items:
                raise ConfigError("The especification for `%s' was not found"
                                  % name)
            value = items.pop(name)
            if ',' not in value:
                raise ConfigError("Invalid value format for `%s'" % name)
            x, y = value.split(',')
            x = int(x or 0)
            y = int(y or 0)
            if x < 0 or y < 0:
                raise ConfigError("Negative values aren't allowed")
            coordinates[name] = (x, y)
        if items:
            raise ConfigError("The name(s) %s are invalid, busted "
                              "configuration" % ", ".join(items.keys()))
        return BankConfiguration(bank_name, coordinates)


class ChequePrinter(BasePrinter):
    def __init__(self, brand=None, model=None, device=None, config_file=None,
                 *args, **kwargs):
        BasePrinter.__init__(self, brand, model, device, config_file, *args,
                             **kwargs)
        if IChequePrinter not in providedBy(self._driver):
            raise DoesNotImplement("The driver %r doesn't implements the "
                                   "IChequePrinter interface" % self._driver)
        self._charset = self._driver.cheque_printer_charset

    def _format_text(self, text):
        return encode_text(text, self._charset)

    #
    # IChequePrinter interface
    #

    def get_banks(self):
        self.info("get_banks")
        return self._driver.get_banks()

    def print_cheque(self, bank: object, value: Real, thirdparty: str,
                     city: str, date: Optional[datetime.datetime]=None):
        if date is None:
            date = datetime.datetime.now()
        self.info('print_cheque')
        return self._driver.print_cheque(bank, value,
                                         self._format_text(thirdparty),
                                         self._format_text(city), date)

    def get_capabilities(self):
        self.info("get_capabilities")
        return self._driver.get_capabilities()

#
# Testing
#


if __name__ == "__main__":
    printer = ChequePrinter()

    # Hmmm, this is not the right way of to do, but... hmm, I just don't know
    # what kind of the cheque the user wants to test, so let me get anyone.
    banks = printer.get_banks()
    bank = banks[list(banks.keys())[0]]
    printer.print_cheque(bank, 6.66, "Henrique Romano", "São Paulo")
