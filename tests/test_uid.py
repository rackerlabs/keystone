from keystone import exception
from keystone import test
from keystone.common import uid


DEFAULT_LEN = 25
MAX_LEN = 64


class UidTest(test.TestCase):
    def test_default_length(self):
        self.assertEqual(len(uid.new()), DEFAULT_LEN)

    def test_shorter_min_length(self):
        self.assertEqual(len(uid.new(min_length=DEFAULT_LEN - 1)), DEFAULT_LEN)

    def test_equal_min_length(self):
        self.assertEqual(len(uid.new(min_length=DEFAULT_LEN)), DEFAULT_LEN)

    def test_longer_min_length(self):
        self.assertEqual(
            len(uid.new(min_length=DEFAULT_LEN + 1)),
            DEFAULT_LEN + 1)

    def test_explicit_shorter_length(self):
        self.assertEqual(len(uid.new(length=DEFAULT_LEN - 1)), DEFAULT_LEN - 1)

    def test_explicit_longer_length(self):
        with self.assertRaises(exception.ValidationError):
            uid.new(length=MAX_LEN + 1)

    def test_conf_shorter_length(self):
        self.opt(uid_length=DEFAULT_LEN - 1)
        self.assertEqual(len(uid.new()), DEFAULT_LEN - 1)

    def test_conf_longer_length(self):
        self.opt(uid_length=MAX_LEN + 1)
        with self.assertRaises(exception.ValidationError):
            uid.new()
