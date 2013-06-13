
from keystoneclient.v2_0 import client as ks_client

from keystone import test

import default_fixtures


class TestNoAdminTokenAuth(test.TestCase):
    def setUp(self):
        super(TestNoAdminTokenAuth, self).setUp()
        self.load_backends()
        self.load_fixtures(default_fixtures)

        self.identity_api.update_metadata(
            self.user_foo['id'], self.tenant_bar['id'],
            dict(roles=[self.role_admin['id']], is_admin='1'))

    def test_request_no_admin_token_auth(self):
        admin_server = self.serveapp('no_admin_token_auth', name='admin')
        try:
            admin_port = admin_server.socket_info['socket'][1]
            admin_endpoint = "http://localhost:%s/v2.0" % admin_port

            kc = ks_client.Client(auth_url=admin_endpoint,
                                  username=self.user_foo['name'],
                                  password=self.user_foo['password'],
                                  tenant_id=self.tenant_bar['id'])

            # If the following does not raise, then the test is successful.
            kc.tenants.list()
        finally:
            admin_server.kill()
