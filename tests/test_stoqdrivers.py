import unittest

from stoqdrivers import __version__


class TestStoqdrivers(unittest.TestCase):
    def test_package_version(self):
        self.assertEquals(__version__, (1, 8, 1))