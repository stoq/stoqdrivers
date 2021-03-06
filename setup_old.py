#!/usr/bin/env python

# Setup file for StoqDrivers
# Code by Async Open Source <http://www.async.com.br>

from setuptools import setup, find_packages


install_requires = [
    "babel",
    "pillow",
    "pyserial >= 2.2",
    "pyusb",
    "qrcode ~= 5.3",
    "zope.interface >= 3.0",
]

setup(
    name="stoqdrivers",
    version="2.0.1",
    author="Async Open Source",
    author_email="stoq-devel@async.com.br",
    description="Python fiscal printer (ECF) drivers",
    long_description=("This package provices device drivers "
                      "for fiscal printers, ECF (Emissor de Coupon Fiscal) "
                      "written in Python. Supports printers from Bematech, "
                      "Daruma, Dataregis, Perto, Sweda and the generic "
                      "FiscNET protocol."),
    url="http://www.stoq.com.br",
    license="GNU LGPL 2.1 (see COPYING)",
    packages=find_packages(exclude=['tests']),
    install_requires=install_requires,
)
