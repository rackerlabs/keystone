
import nose.exc

from core import CompatTestCase
from client import KeystoneClientTests
from core import KEYSTONECLIENT_REPO


class Kc11TestCase(CompatTestCase, KeystoneClientTests):
    def get_checkout(self):
        return KEYSTONECLIENT_REPO, '0.1.1'

    def test_policy_crud(self):
        raise nose.exc.SkipTest('N/A')
