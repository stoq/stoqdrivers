# Stoqdrivers

Stoqdrivers has as goal the implementation of drivers for the most
common equipments that interacts with retail systems. The main
example usage of this package is in Stoq: http://www.stoq.com.br.

## Requirements

    * Python 3 (http://www.python.org/)
    * pySerial 1.3 (http://pyserial.sourceforge.net/)
    * pyUSB 1.3 (https://walac.github.io/pyusb/)
    * Zope interfaces 3.5.2 (http://www.zope.org/Products/ZopeInterface/)

## New Versions

New versions of the package can be found always by the gerrit repository:

    http://gerrit.async.com.br/stoqdrivers

There's also a mirror at github:

    $ git clone http://github.com/stoq/stoqdrivers.git

## Mailing list

There are two mailing lists where you can put questions and suggestions
about Stoqdrivers. You can subscribe to them through the web interface
at:

    * http://www.async.com.br/mailman/listinfo/stoq-users
    * http://www.async.com.br/mailman/listinfo/stoq-devel

## Starting a server to have a ethernet connection

To start the echo server to do simple tests just run the following command

```
./bin/echo_server
```
