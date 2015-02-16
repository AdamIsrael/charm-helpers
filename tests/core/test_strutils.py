import unittest

import charmhelpers.core.strutils as strutils


class TestStrUtils(unittest.TestCase):
    def setUp(self):
        super(TestStrUtils, self).setUp()

    def tearDown(self):
        super(TestStrUtils, self).tearDown()

    def test_bool_from_string(self):
        self.assertTrue(strutils.bool_from_string('true'))
        self.assertTrue(strutils.bool_from_string('True'))
        self.assertTrue(strutils.bool_from_string('yes'))
        self.assertTrue(strutils.bool_from_string('Yes'))
        self.assertTrue(strutils.bool_from_string('y'))
        self.assertTrue(strutils.bool_from_string('Y'))

        self.assertFalse(strutils.bool_from_string('False'))
        self.assertFalse(strutils.bool_from_string('false'))
        self.assertFalse(strutils.bool_from_string('no'))
        self.assertFalse(strutils.bool_from_string('No'))
        self.assertFalse(strutils.bool_from_string('n'))
        self.assertFalse(strutils.bool_from_string('N'))

        self.assertRaises(ValueError, strutils.bool_from_string, 'foo')
        self.assertFalse(strutils.bool_from_string('foo', fatal=False))
