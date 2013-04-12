from keystone import exception
from keystone import test
from keystone.common import uid
from keystone.common import config


class UidTest(test.TestCase):
    def setUp(self):
        super(UidTest, self).setUp()

        # reset the default uid_length
        self.opt(uid_length=config._DEFAULT_UID_LENGTH)

    def test_default_length(self):
        self.assertEqual(len(uid.new()), 32)

    def test_shorter_min_length(self):
        self.assertEqual(len(uid.new(min_length=31)), 32)

    def test_equal_min_length(self):
        self.assertEqual(len(uid.new(min_length=32)), 32)

    def test_longer_min_length(self):
        self.assertEqual(len(uid.new(min_length=33)), 33)

    def test_explicit_shorter_length(self):
        self.assertEqual(len(uid.new(length=31)), 31)

    def test_explicit_longer_length(self):
        with self.assertRaises(exception.UnexpectedError):
            uid.new(length=65)

    def test_conf_shorter_length(self):
        self.opt(uid_length=31)
        self.assertEqual(len(uid.new()), 31)

    def test_conf_longer_length(self):
        self.opt(uid_length=65)
        with self.assertRaises(exception.UnexpectedError):
            uid.new()
