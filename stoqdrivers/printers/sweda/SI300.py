# -*- Mode: Python; coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Stoqdrivers
## Copyright (C) 2017-2019 Stoq Tecnologia <http://stoq.com.br>
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

from zope.interface import implementer

from stoqdrivers.serialbase import SerialBase
from stoqdrivers.escpos import EscPosMixin, ESC
from stoqdrivers.interfaces import INonFiscalPrinter


@implementer(INonFiscalPrinter)
class SI300(SerialBase, EscPosMixin):
    LINE_FEED = '\x0a'

    FLAG_CONDENSED = 0  # 1
    FLAG_BOLD = 3  # 8
    FLAG_DOUBLE_HEIGHT = 4  # 16

    max_characters = 56
    supported = True
    model_name = "Sweda SI-300"

    def __init__(self, port, consts=None):
        self._text_mode = 0
        SerialBase.__init__(self, port)
        EscPosMixin.__init__(self)

    def _set_text_mode(self, mode):
        self._text_mode = mode
        self.write(ESC + '!' + chr(mode))

    def set_condensed(self):
        mode = self._text_mode | (2 ** self.FLAG_CONDENSED)
        self._set_text_mode(mode)

    def unset_condensed(self):
        mode = self._text_mode & ~(2 ** self.FLAG_CONDENSED)
        self._set_text_mode(mode)

    def set_bold(self):
        mode = self._text_mode | (2 ** self.FLAG_BOLD)
        self._set_text_mode(mode)

    def unset_bold(self):
        mode = self._text_mode & ~(2 ** self.FLAG_BOLD)
        self._set_text_mode(mode)

    def set_double_height(self):
        mode = self._text_mode | (2 ** self.FLAG_DOUBLE_HEIGHT)
        self._set_text_mode(mode)

    def unset_double_height(self):
        mode = self._text_mode & ~(2 ** self.FLAG_DOUBLE_HEIGHT)
        self._set_text_mode(mode)

    def print_matrix(self, matrix, api=None, linefeed=True, multiplier=None):
        # Unset condensed to prevent blank spaces between lines
        was_condensed = self._text_mode & (2 ** self.FLAG_CONDENSED)
        self.unset_condensed()
        super().print_matrix(matrix, api, linefeed, multiplier=multiplier)
        # Reset the previous state if necessary
        if was_condensed:
            self.set_condensed()
