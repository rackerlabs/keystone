
import uuid
import webob

from core import CompatTestCase
from client import KeystoneClientTests
from core import KEYSTONECLIENT_REPO, DEFAULT_DOMAIN_ID

from keystone.openstack.common import jsonutils


class KcMasterTestCase(CompatTestCase, KeystoneClientTests):
    def get_checkout(self):
        return KEYSTONECLIENT_REPO, 'master'

    def test_tenant_add_and_remove_user(self):
        client = self.get_client(admin=True)
        client.roles.add_user_role(tenant=self.tenant_bar['id'],
                                   user=self.user_two['id'],
                                   role=self.role_other['id'])
        user_refs = client.tenants.list_users(tenant=self.tenant_bar['id'])
        self.assert_(self.user_two['id'] in [x.id for x in user_refs])
        client.roles.remove_user_role(tenant=self.tenant_bar['id'],
                                      user=self.user_two['id'],
                                      role=self.role_other['id'])
        roles = client.roles.roles_for_user(user=self.user_foo['id'],
                                            tenant=self.tenant_bar['id'])
        self.assertNotIn(self.role_other['id'], roles)
        user_refs = client.tenants.list_users(tenant=self.tenant_bar['id'])
        self.assertNotIn(self.user_two['id'], [x.id for x in user_refs])

    def test_user_role_add_404(self):
        from keystoneclient import exceptions as client_exceptions
        client = self.get_client(admin=True)
        self.assertRaises(client_exceptions.NotFound,
                          client.roles.add_user_role,
                          tenant=uuid.uuid4().hex,
                          user=self.user_foo['id'],
                          role=self.role_member['id'])
        self.assertRaises(client_exceptions.NotFound,
                          client.roles.add_user_role,
                          tenant=self.tenant_baz['id'],
                          user=uuid.uuid4().hex,
                          role=self.role_member['id'])
        self.assertRaises(client_exceptions.NotFound,
                          client.roles.add_user_role,
                          tenant=self.tenant_baz['id'],
                          user=self.user_foo['id'],
                          role=uuid.uuid4().hex)

    def test_user_role_remove_404(self):
        from keystoneclient import exceptions as client_exceptions
        client = self.get_client(admin=True)
        self.assertRaises(client_exceptions.NotFound,
                          client.roles.remove_user_role,
                          tenant=uuid.uuid4().hex,
                          user=self.user_foo['id'],
                          role=self.role_member['id'])
        self.assertRaises(client_exceptions.NotFound,
                          client.roles.remove_user_role,
                          tenant=self.tenant_baz['id'],
                          user=uuid.uuid4().hex,
                          role=self.role_member['id'])
        self.assertRaises(client_exceptions.NotFound,
                          client.roles.remove_user_role,
                          tenant=self.tenant_baz['id'],
                          user=self.user_foo['id'],
                          role=uuid.uuid4().hex)
        self.assertRaises(client_exceptions.NotFound,
                          client.roles.remove_user_role,
                          tenant=self.tenant_baz['id'],
                          user=self.user_foo['id'],
                          role=self.role_member['id'])

    def test_tenant_list_marker(self):
        client = self.get_client()

        # Add two arbitrary tenants to user for testing purposes
        for i in range(2):
            tenant_id = uuid.uuid4().hex
            tenant = {'name': 'tenant-%s' % tenant_id, 'id': tenant_id,
                      'domain_id': DEFAULT_DOMAIN_ID}
            self.identity_api.create_project(tenant_id, tenant)
            self.identity_api.add_user_to_project(tenant_id,
                                                  self.user_foo['id'])

        tenants = client.tenants.list()
        self.assertEqual(len(tenants), 3)

        tenants_marker = client.tenants.list(marker=tenants[0].id)
        self.assertEqual(len(tenants_marker), 2)
        self.assertEqual(tenants[1].name, tenants_marker[0].name)
        self.assertEqual(tenants[2].name, tenants_marker[1].name)

    def test_tenant_list_marker_not_found(self):
        from keystoneclient import exceptions as client_exceptions

        client = self.get_client()
        self.assertRaises(client_exceptions.BadRequest,
                          client.tenants.list, marker=uuid.uuid4().hex)

    def test_tenant_list_limit(self):
        client = self.get_client()

        # Add two arbitrary tenants to user for testing purposes
        for i in range(2):
            tenant_id = uuid.uuid4().hex
            tenant = {'name': 'tenant-%s' % tenant_id, 'id': tenant_id,
                      'domain_id': DEFAULT_DOMAIN_ID}
            self.identity_api.create_project(tenant_id, tenant)
            self.identity_api.add_user_to_project(tenant_id,
                                                  self.user_foo['id'])

        tenants = client.tenants.list()
        self.assertEqual(len(tenants), 3)

        tenants_limited = client.tenants.list(limit=2)
        self.assertEqual(len(tenants_limited), 2)
        self.assertEqual(tenants[0].name, tenants_limited[0].name)
        self.assertEqual(tenants[1].name, tenants_limited[1].name)

    def test_tenant_list_limit_bad_value(self):
        from keystoneclient import exceptions as client_exceptions

        client = self.get_client()
        self.assertRaises(client_exceptions.BadRequest,
                          client.tenants.list, limit='a')
        self.assertRaises(client_exceptions.BadRequest,
                          client.tenants.list, limit=-1)

    def test_roles_get_by_user(self):
        client = self.get_client(admin=True)
        roles = client.roles.roles_for_user(user=self.user_foo['id'],
                                            tenant=self.tenant_bar['id'])
        self.assertTrue(len(roles) > 0)

    def test_user_can_update_passwd(self):
        client = self.get_client(self.user_two)

        token_id = client.auth_token
        new_password = uuid.uuid4().hex

        # TODO(derekh) : Update to use keystoneclient when available
        class FakeResponse(object):
            def start_fake_response(self, status, headers):
                self.response_status = int(status.split(' ', 1)[0])
                self.response_headers = dict(headers)
        responseobject = FakeResponse()

        req = webob.Request.blank(
            '/v2.0/OS-KSCRUD/users/%s' % self.user_two['id'],
            headers={'X-Auth-Token': token_id})
        req.method = 'PATCH'
        req.body = ('{"user":{"password":"%s","original_password":"%s"}}' %
                    (new_password, self.user_two['password']))
        self.public_server.application(req.environ,
                                       responseobject.start_fake_response)

        self.user_two['password'] = new_password
        self.get_client(self.user_two)

    def test_user_cannot_update_other_users_passwd(self):
        from keystoneclient import exceptions as client_exceptions

        client = self.get_client(self.user_two)

        token_id = client.auth_token
        new_password = uuid.uuid4().hex

        # TODO(derekh) : Update to use keystoneclient when available
        class FakeResponse(object):
            def start_fake_response(self, status, headers):
                self.response_status = int(status.split(' ', 1)[0])
                self.response_headers = dict(headers)
        responseobject = FakeResponse()

        req = webob.Request.blank(
            '/v2.0/OS-KSCRUD/users/%s' % self.user_foo['id'],
            headers={'X-Auth-Token': token_id})
        req.method = 'PATCH'
        req.body = ('{"user":{"password":"%s","original_password":"%s"}}' %
                    (new_password, self.user_two['password']))
        self.public_server.application(req.environ,
                                       responseobject.start_fake_response)
        self.assertEquals(403, responseobject.response_status)

        self.user_two['password'] = new_password
        self.assertRaises(client_exceptions.Unauthorized,
                          self.get_client, self.user_two)

    def test_tokens_after_user_update_passwd(self):
        from keystoneclient import exceptions as client_exceptions

        client = self.get_client(self.user_two)

        token_id = client.auth_token
        new_password = uuid.uuid4().hex

        # TODO(derekh) : Update to use keystoneclient when available
        class FakeResponse(object):
            def start_fake_response(self, status, headers):
                self.response_status = int(status.split(' ', 1)[0])
                self.response_headers = dict(headers)
        responseobject = FakeResponse()

        req = webob.Request.blank(
            '/v2.0/OS-KSCRUD/users/%s' % self.user_two['id'],
            headers={'X-Auth-Token': token_id})
        req.method = 'PATCH'
        req.body = ('{"user":{"password":"%s","original_password":"%s"}}' %
                    (new_password, self.user_two['password']))

        rv = self.public_server.application(
            req.environ,
            responseobject.start_fake_response)
        response_json = jsonutils.loads(rv.pop())
        new_token_id = response_json['access']['token']['id']

        self.assertRaises(client_exceptions.Unauthorized, client.tenants.list)
        client.auth_token = new_token_id
        client.tenants.list()
