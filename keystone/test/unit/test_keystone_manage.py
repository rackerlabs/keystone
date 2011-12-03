import os
import subprocess
import unittest2 as unittest

# Calculate root path so ewe call files in bin
possible_topdir = os.path.normpath(os.path.join(os.path.abspath(__file__),
                                   os.pardir,
                                   os.pardir,
                                   os.pardir,
                                   os.pardir))


class TestKeystoneManage(unittest.TestCase):
    """
    Functional tests for the keystone-manage client.
    """

    def test_keystone_manage_usage(self):
        """
        Test that we can call ``keystone-manage --help``
        """
        cmd = [
            os.path.join(possible_topdir, 'bin', 'keystone-manage'),
            '--help',
        ]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        result = process.communicate()[0]
        self.assertIn('usage', result)
        self.assertIn('version', result)

    def test_version_help(self):
        """
        Test that we can call ``keystone-manage version --help``
        """
        cmd = [
            os.path.join(possible_topdir, 'bin', 'keystone-manage'),
            'version', '--help',
        ]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        result = process.communicate()[0]
        self.assertIn('usage: version [-h] [--api] [--implementation]', result)


if __name__ == '__main__':
    unittest.main()
