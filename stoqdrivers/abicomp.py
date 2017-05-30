# -*- Mode: Python; coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Stoqdrivers
## Copyright (C) 2007 Async Open Source <http://www.async.com.br>
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
## Author(s):   Johan Dahlin    <jdahlin@async.com.br>
##

# This module implements the ABICOMP codec for python

TABLE = {
    'À': b'\xa1',
    'Á': b'\xa2',
    'Â': b'\xa3',
    'Ã': b'\xa4',
    'Ä': b'\xa5',
    'Ç': b'\xa6',
    'È': b'\xa7',
    'É': b'\xa8',
    'Ê': b'\xa9',
    'Ë': b'\xaa',
    'Ì': b'\xab',
    'Í': b'\xac',
    'Î': b'\xad',
    'Ï': b'\xae',
    'Ñ': b'\xaf',

    'Ò': b'\xb0',
    'Ó': b'\xb1',
    'Ô': b'\xb2',
    'Õ': b'\xb3',
    'Ö': b'\xb4',
    'Œ': b'\xb5',
    'Ù': b'\xb6',
    'Ú': b'\xb7',
    'Û': b'\xb8',
    'Ü': b'\xb9',
    'Ÿ': b'\xba',
    '˝': b'\xbb',
    '£': b'\xbc',
    'ʻ': b'\xbd',
    '°': b'\xbe',

    '¡': b'\xc0',
    'à': b'\xc1',
    'á': b'\xc2',
    'â': b'\xc3',
    'ã': b'\xc4',
    'ä': b'\xc5',
    'ç': b'\xc6',
    'è': b'\xc7',
    'é': b'\xc8',
    'ê': b'\xc9',
    'ë': b'\xca',
    'ì': b'\xcb',
    'í': b'\xcc',
    'î': b'\xcd',
    'ï': b'\xce',
    'ñ': b'\xcf',

    'ò': b'\xd0',
    'ó': b'\xd1',
    'ô': b'\xd2',
    'õ': b'\xd3',
    'ö': b'\xd4',
    'œ': b'\xd5',
    'ù': b'\xd6',
    'ú': b'\xd7',
    'û': b'\xd8',
    'ü': b'\xd9',
    'ÿ': b'\xda',
    'ß': b'\xdb',
    'ª': b'\xdc',
    'º': b'\xdd',
    '¿': b'\xde',
    '±': b'\xdf',
}
RTABLE = dict([(v, k) for k, v in TABLE.items()])


def encode(input):
    """
    Convert unicode to string.
    @param input: text to encode
    @type input: unicode
    @returns: encoded text
    @rtype: str
    """
    return [TABLE.get(c) or c.encode() for c in input]


def decode(input):
    """
    Convert string in unicode.
    @param input: text to decode
    @type input: str
    @returns: decoded text
    @rtype: unicode
    """
    # Iterating over bytes produces a sequence of integers
    bytes_ = [(c, bytes([c])) for c in input]
    return [RTABLE.get(b) or chr(i) for i, b in bytes_]


def register_codec():
    import codecs

    class Codec(codecs.Codec):
        def encode(self, input, errors='strict'):
            if not input:
                return b"", 0
            output = encode(input)
            return b"".join(output), len(output)

        def decode(self, input, errors='strict'):
            if not input:
                return u"", 0
            output = decode(input)
            return u"".join(output), len(output)

    class StreamWriter(Codec, codecs.StreamWriter):
        pass

    class StreamReader(Codec, codecs.StreamReader):
        pass

    def getregentry(encoding):
        if encoding != 'abicomp':
            return None
        return (Codec().encode,
                Codec().decode,
                StreamReader,
                StreamWriter)

    codecs.register(getregentry)


def test():
    register_codec()
    all = u''.join(TABLE.keys())
    assert all == all.encode('abicomp').decode('abicomp')

    mixed = u'não dîz'
    assert mixed == mixed.encode('abicomp').decode('abicomp')


if __name__ == '__main__':
    test()
