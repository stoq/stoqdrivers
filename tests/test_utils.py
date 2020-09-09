import unittest

from stoqdrivers.utils import get_obj_from_module


class TestUtils(unittest.TestCase):
    def test_get_obj_from_module(self):
        with self.assertRaises(ImportError):
            get_obj_from_module('stoqdrivers.does.not.exists.I.hope', obj_name='FooBarBaz')

        with self.assertRaises(ImportError):
            get_obj_from_module('stoqdrivers.utils', obj_name='FooBarBazDoesNotExists')

        obj = get_obj_from_module('stoqdrivers.utils', obj_name='get_obj_from_module')
        self.assertEquals(obj, get_obj_from_module)
