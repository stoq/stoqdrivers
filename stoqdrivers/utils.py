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
Functions for general use.
"""

import codecs
from importlib import import_module
import unicodedata

GRAPHICS_8BITS = 8
GRAPHICS_24BITS = 24


def encode_text(text, encoding):
    """ Converts the string 'text' to encoding 'encoding' and optionally
    normalizes the string (currently only for ascii)

    @param text:       text to convert
    @type text:        str
    @param encoding:   encoding to use
    @type text:        str
    @returns:          converted text
    """
    if encoding == "ascii":
        text = unicodedata.normalize("NFKD", text)
    # If we use text.encode we will get this sometimes:
    # TypeError: 'abicomp' encoder returned 'str' instead of 'bytes';
    #   use codecs.encode() to encode to arbitrary types
    text = codecs.encode(text, encoding, "ignore")
    # Only do the bellow conversion if the encoding above worked
    if isinstance(text, bytes):
        # Use bytes2str instead of decode or otherwise we would encode
        # the bytes in unicode. This way we will still keep them in the
        # encoding that we want (since SerialBase.write will do the reversal
        # operation, str2bytes) even though we will get some strange
        # characters in the "unicode version" of the string
        text = bytes2str(text)
    return text


def decode_text(text, encoding):
    """Decode the text using the given encoding."""
    bytes_ = str2bytes(text)
    decoded_text = codecs.decode(bytes_, encoding, "ignore")
    # If the  decoding above failed return the original string
    if isinstance(text, bytes):
        return text
    return decoded_text


def str2bytes(text):
    if isinstance(text, bytes):
        return text
    return bytes(ord(i) for i in text)


def bytes2str(data):
    return ''.join(chr(i) for i in data)


def bits2byte(bits):
    return sum(2 ** i if bit else 0 for i, bit in enumerate(reversed(bits)))


def matrix2graphics(graphics_api, matrix, max_cols, multiplier=1, centralized=True):
    if graphics_api not in (GRAPHICS_8BITS, GRAPHICS_24BITS):
        raise ValueError("Graphics api %s not supported" % (graphics_api, ))

    sub_len = int(graphics_api / multiplier)

    for i in range(0, len(matrix), sub_len):
        bytes_ = []
        sub = matrix[i:i + sub_len]
        if len(sub) < sub_len:
            sub.extend([[False] * len(matrix[0])] * (sub_len - len(sub)))

        for j in range(len(matrix[0])):
            bits = []
            for bit in sub:
                bits.extend([bit[j]] * multiplier)

            if graphics_api == GRAPHICS_8BITS:
                # The 3 is to compensate for the fact that each pixel is
                # 3x larger vertically than horizontally
                bytes_.extend([bits2byte(bits)] * 3 * multiplier)
            elif graphics_api == GRAPHICS_24BITS:
                splitted_bytes = []
                for k in range(0, 24, 8):
                    splitted_bytes.append(bits2byte(bits[k: k + 8]))
                bytes_.extend(splitted_bytes * multiplier)
            else:
                raise AssertionError

        if centralized:
            diff = max_cols - len(bytes_)
            if diff:
                bytes_ = ([0] * int(diff / 2)) + bytes_

        divide_len_by = graphics_api / 8
        yield ''.join(chr(b) for b in bytes_), int(len(bytes_) / divide_len_by)


def get_obj_from_module(module_name, obj_name):
    module = import_module(module_name)
    try:
        return getattr(module, obj_name)
    except AttributeError:
        raise ImportError("Can't find class %s for module %s" % (module_name, module_name))
