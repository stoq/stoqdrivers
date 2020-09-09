#!/usr/bin/env python

# Setup file for StoqDrivers
# Code by Async Open Source <http://www.async.com.br>

from setuptools import setup, find_packages


with open('requirements.txt') as f:
    install_requires = [l.strip() for l in f.readlines() if
                        l.strip() and not l.startswith('#')]

setup(
    name="stoqdrivers",
    version="1.8.1",
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
