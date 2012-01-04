#!/usr/bin/env python

# Setup file for StoqDrivers
# Code by Async Open Source <http://www.async.com.br>

#
# Dependency checking
#

dependencies = [('ZopeInterface', 'zope.interface', '3.0',
                 'http://www.zope.org/Products/ZopeInterface',
                 None),
                ('kiwi', 'kiwi', (1, 9, 28),
                 'http://www.async.com.br/projects/kiwi/',
                 lambda x: x.kiwi_version),
                ('PySerial', 'serial', '2.1',
                 'http://pyserial.sourceforge.net',
                 None)]
for package_name, module_name, version, url, get_version in dependencies:
    try:
        module = __import__(module_name, {}, {}, [])
    except ImportError:
        raise SystemExit("The '%s' module could not be found\n"
                         "Please install %s which can be found at %s" % (
            module_name, package_name, url))

    if not get_version:
        continue

    if version > get_version(module):
        raise SystemExit(
            "The '%s' module was found but it was not recent enough\n"
            "Please install at least version %s of %s" % (
            module_name, version, package_name))

#
# Package installation
#

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
    install_requires="kiwi-gtk >= 1.9.28",
    )

