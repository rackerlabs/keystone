import nose

from core import CompatTestCase
from core import KEYSTONECLIENT_REPO
from client import KeystoneClientTests


class KcEssex3TestCase(CompatTestCase, KeystoneClientTests):
    def get_checkout(self):
        return KEYSTONECLIENT_REPO, 'essex-3'

    def test_tenant_add_and_remove_user(self):
        client = self.get_client(admin=True)
        client.roles.add_user_to_tenant(tenant_id=self.tenant_bar['id'],
                                        user_id=self.user_two['id'],
                                        role_id=self.role_member['id'])
        role_refs = client.roles.get_user_role_refs(
            user_id=self.user_two['id'])
        self.assert_(self.tenant_baz['id'] in [x.tenantId for x in role_refs])

        # get the "role_refs" so we get the proper id, this is how the clients
        # do it
        roleref_refs = client.roles.get_user_role_refs(
            user_id=self.user_two['id'])
        for roleref_ref in roleref_refs:
            if (roleref_ref.roleId == self.role_member['id']
                    and roleref_ref.tenantId == self.tenant_baz['id']):
                # use python's scope fall through to leave roleref_ref set
                break

        client.roles.remove_user_from_tenant(tenant_id=self.tenant_bar['id'],
                                             user_id=self.user_two['id'],
                                             role_id=roleref_ref.id)

        role_refs = client.roles.get_user_role_refs(
            user_id=self.user_two['id'])
        self.assert_(self.tenant_baz['id'] not in
                     [x.tenantId for x in role_refs])

    def test_roles_get_by_user(self):
        client = self.get_client(admin=True)
        roles = client.roles.get_user_role_refs(user_id='foo')
        self.assertTrue(len(roles) > 0)

    def test_role_list_404(self):
        raise nose.exc.SkipTest('N/A')

    def test_authenticate_and_delete_token(self):
        raise nose.exc.SkipTest('N/A')

    def test_user_create_update_delete(self):
        from keystoneclient import exceptions as client_exceptions

        test_username = 'new_user'
        client = self.get_client(admin=True)
        user = client.users.create(name=test_username,
                                   password='password',
                                   email='user1@test.com')
        self.assertEquals(user.name, test_username)

        user = client.users.get(user=user.id)
        self.assertEquals(user.name, test_username)

        user = client.users.update_email(user=user, email='user2@test.com')
        self.assertEquals(user.email, 'user2@test.com')

        # NOTE(termie): update_enabled doesn't return anything, probably a bug
        client.users.update_enabled(user=user, enabled=False)
        user = client.users.get(user.id)
        self.assertFalse(user.enabled)

        self.assertRaises(client_exceptions.Unauthorized,
                          self._client,
                          username=test_username,
                          password='password')
        client.users.update_enabled(user, True)

        user = client.users.update_password(user=user, password='password2')

        self._client(username=test_username,
                     password='password2')

        user = client.users.update_tenant(user=user, tenant='bar')
        # TODO(ja): once keystonelight supports default tenant
        #           when you login without specifying tenant, the
        #           token should be scoped to tenant 'bar'

        client.users.delete(user.id)
        self.assertRaises(client_exceptions.NotFound, client.users.get,
                          user.id)

    def test_user_update_404(self):
        raise nose.exc.SkipTest('N/A')

    def test_endpoint_create_404(self):
        raise nose.exc.SkipTest('N/A')

    def test_endpoint_delete_404(self):
        raise nose.exc.SkipTest('N/A')

    def test_policy_crud(self):
        """Due to lack of endpoint CRUD"""
        raise nose.exc.SkipTest('N/A')
