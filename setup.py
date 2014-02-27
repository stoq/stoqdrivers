#!/usr/bin/env python

# Setup file for StoqDrivers
# Code by Async Open Source <http://www.async.com.br>

from kiwi.dist import setup, listpackages, listfiles

from stoqdrivers import __version__


setup(
    name="stoqdrivers",
    version= ".".join(map(str, __version__)),
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
    packages=listpackages('stoqdrivers'),
    data_files=[
    ("$datadir/conf", listfiles("stoqdrivers/conf", "*.ini"))],
    global_resources=dict(conf="$datadir/conf"),
    resources=dict(locale="$prefix/share/locale"),
    install_requires=[
        "kiwi-gtk >= 1.9.28",
        "zope.interface >= 3.0",
        "pyserial >= 2.2",
    ]
    )

