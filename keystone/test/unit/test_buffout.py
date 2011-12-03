import unittest2 as unittest
import sys

from keystone.tools import buffout


class TestStdoutIdentity(unittest.TestCase):
    def test_stdout_after_init(self):
        stdout = sys.stdout
        buffout.OutputBuffer()

        self.assertTrue(sys.stdout is stdout,
            "sys.stdout was replaced")

    def test_stdout_replaced(self):
        stdout = sys.stdout
        ob = buffout.OutputBuffer()
        ob.start()

        self.assertTrue(sys.stdout is not stdout,
            "sys.stdout not replaced")

        ob.stop()

    def test_stdout_recovery(self):
        stdout = sys.stdout
        ob = buffout.OutputBuffer()
        ob.start()
        ob.stop()

        self.assertTrue(sys.stdout is stdout,
            "sys.stdout not restored")


class TestOutputBufferContents(unittest.TestCase):
    def setUp(self):
        self.ob = buffout.OutputBuffer()
        self.ob.start()

    def tearDown(self):
        self.ob.stop()

    def test_read_contents(self):
        print 'foobar'
        print 'wompwomp'
        output = self.ob.read()
        self.assertEquals(len(output), 16, output)
        self.assertIn('foobar', output)
        self.assertIn('ompwom', output)

    def test_read_lines(self):
        print 'foobar'
        print 'wompwomp'
        lines = self.ob.read_lines()
        self.assertTrue(isinstance(lines, list))
        self.assertEqual(len(lines), 2)
        self.assertIn('foobar', lines)
        self.assertIn('wompwomp', lines)
