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
## Author(s):   Evandro Vale Miquelito      <evandro@async.com.br>
##
"""
stoqdrivers/constants.py:
    
    StoqDrivers constants
"""


# Constants for product unit labels
(UNIT_WEIGHT,
 UNIT_METERS,
 UNIT_LITERS,
 UNIT_EMPTY)  = range(4)

(TAX_IOF,
 TAX_ICMS,
 TAX_SUBSTITUTION,
 TAX_EXEMPTION,
 TAX_NONE) = range(5)

#
# Constants for Payment Method
#

(
    MONEY_PM,
    CHEQUE_PM
) = range(2)
