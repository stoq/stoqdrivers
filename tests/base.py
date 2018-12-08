import os
import unittest

from zope.interface import implementer

import stoqdrivers
from stoqdrivers.interfaces import ISerialPort
from stoqdrivers.serialbase import SerialPort


# The directory where tests data will be stored
RECORDER_DATA_DIR = "data"


@implementer(ISerialPort)
class LogSerialPort:
    """ A decorator for the SerialPort object expected by the driver to test,
    responsible for log all the bytes read/written.
    """

    def __init__(self, port):
        self._port = port
        self._bytes = []
        self._last = None
        self._buffer = ''

    def setDTR(self):
        return self._port.setDTR()

    def getDSR(self):
        return self._port.getDSR()

    @property
    def parity(self):
        return self._port.parity

    @parity.setter
    def parity(self, value):
        self._port.parity = value

    @property
    def timeout(self):
        return self._port.timeout

    @timeout.setter
    def timeout(self, value):
        self._port.timeout = value

    @property
    def writeTimeout(self):
        return self._port.writeTimeout

    @writeTimeout.setter
    def writeTimeout(self, value):
        self._port.writeTimeout = value

    def read(self, n_bytes=1):
        data = self._port.read(n_bytes)
        self._buffer += data
        self._last = 'R'
        return data

    def write(self, bytes):
        if self._last == 'R':
            self._bytes.append(('R', self._buffer))
            self._buffer = ''

        self._bytes.append(('W', bytes))
        self._port.write(bytes)
        self._last = 'W'

    def save(self, filename):
        if self._buffer:
            self._bytes.append(('R', self._buffer))
        fd = open(filename, "w")
        for type, line in self._bytes:
            fd.write("%s %s\n" % (type, repr(line)[1:-1]))
        fd.close()


@implementer(ISerialPort)
class PlaybackPort:

    def __init__(self, datafile):
        self._input = []
        self._output = b''
        self._datafile = datafile
        self._load_data(datafile)

    def setDTR(self):
        pass

    def getDSR(self):
        return True

    def write(self, bytes_):
        n_bytes = len(bytes_)
        data = bytes(self._input[:n_bytes])
        self._input = bytes(self._input[n_bytes:])

        if bytes_ != data:
            raise ValueError("Written data differs from the expected:\n"
                             "FILE:     %s\n"
                             "EXPECTED: %r\n"
                             "GOT:      %r\n" % (self._datafile, data, bytes_))

    def read(self, n_bytes=1):
        data = self._output[:n_bytes]
        if not data:
            return None
        self._output = self._output[n_bytes:]
        return data

    def _convert_data(self, data):
        data = data.replace(b'\\n', b'\n')
        data = data.replace(b'\\r', b'\r')
        data = data.replace(b'\\t', b'\t')
        data = data.replace(b'\\\\', b'\\')
        data = data.split(b'\\x')
        if len(data) == 1:
            data = data[0]
        else:
            n = b''
            for p in data:
                if len(p) <= 1:
                    n += p
                else:
                    try:
                        data = bytes([int(p[:2], 16)])
                    except:
                        data = p[:2]
                    n += data + p[2:]
            data = n

        return data

    def _load_data(self, datafile):
        fd = open(datafile, "rb")
        for n, line in enumerate(fd.readlines()):
            data = self._convert_data(line[2:-1])

            if line.startswith(b"W"):
                self._input.extend(data)
            elif line.startswith(b"R"):
                self._output += data
            else:
                raise TypeError("Unrecognized entry type at %s:%d: %r"
                                % (datafile, n + 1, line[0]))
        fd.close()


class _BaseTest(unittest.TestCase):
    def __init__(self, test_name):
        self._test_name = test_name
        unittest.TestCase.__init__(self, test_name)

    def tearDown(self):
        filename = self._get_recorder_filename()
        if not os.path.exists(filename):
            self._port.save(filename)

    def setUp(self):
        filename = self._get_recorder_filename()
        if not os.path.exists(filename):
            # Change this path to the serial port and set the baudrate used by
            # fiscal printer when recreating the tests.
            real_port = SerialPort('/tmp/stoq-ecf', baudrate=9600)
            self._port = LogSerialPort(real_port)
        else:
            self._port = PlaybackPort(filename)

        kwargs = self.get_device_init_kwargs()
        self._device = self.device_class(brand=self.brand,
                                         model=self.model,
                                         port=self._port, **kwargs)

    def get_device_init_kwargs(self):
        return {}

    def _get_recorder_filename(self):
        testdir = os.path.join(os.path.dirname(stoqdrivers.__file__),
                               "..", "tests")
        test_name = self._test_name
        if test_name.startswith('test_'):
            test_name = test_name[5:]
        test_name = test_name.replace('_', '-')

        filename = "%s-%s-%s.txt" % (self.brand, self.model, test_name)
        return os.path.join(testdir, RECORDER_DATA_DIR, filename)
