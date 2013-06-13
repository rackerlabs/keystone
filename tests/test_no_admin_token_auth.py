
import io
import webtest

from keystone.openstack.common import jsonutils
from keystone import test

import default_fixtures


def _generate_paste_config():
    # Generate a file, based on keystone-paste.ini, that doesn't include
    # admin_token_auth in the pipeline

    with open(test.etcdir('keystone-paste.ini'), 'r') as f:
        contents = f.read()

    new_contents = contents.replace(' admin_token_auth ', ' ')

    with open('no_admin_token_auth-paste.ini', 'w') as f:
        f.write(new_contents)


class TestNoAdminTokenAuth(test.TestCase):
    def setUp(self):
        super(TestNoAdminTokenAuth, self).setUp()
        self.load_backends()
        self.load_fixtures(default_fixtures)

    def test_request_no_admin_token_auth(self):
        # This test verifies that if the admin_token_auth middleware isn't
        # in the paste pipeline that users can still make requests.

        # Assigns user_foo admin role, user_foo should be able to do admin
        # operations.
        self.identity_api.update_metadata(
            self.user_foo['id'], self.tenant_bar['id'],
            dict(roles=[self.role_admin['id']], is_admin='1'))

        _generate_paste_config()

        admin_app = webtest.TestApp(
            self.loadapp('no_admin_token_auth', name='admin'))

        r = admin_app.request(
            '/v3/auth/tokens',
            method='POST',
            body_file=io.BytesIO(jsonutils.dumps({
                'auth': {
                    'identity': {
                        'methods': ['password'],
                        'password': {
                            'user': {
                                'name': self.user_foo['name'],
                                'password': self.user_foo['password'],
                                'domain': {
                                    'id': self.user_foo['domain_id']
                                }
                            }
                        }
                    },
                    'scope': {
                        'project': {
                            'id': self.tenant_bar['id'],
                        }
                    }
                }
            })))
        token = r.headers.get('X-Subject-Token')

        # If the following does not raise, then the test is successful.
        admin_app.request('/v2.0/tenants', headers={'X-Auth-Token': token})
