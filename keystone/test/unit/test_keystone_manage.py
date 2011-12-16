import subprocess
import unittest


class TestKeystoneManage(unittest.TestCase):
    """
    Functional tests for the keystone-manage client.
    """

    def test_check_can_call_keystone_manage(self):
        """
        Test that we can call keystone-manage
        """
        result = subprocess.check_output(['keystone-manage', '--help'])
        self.assertIn('Usage', result)

if __name__ == '__main__':
    unittest.main()
