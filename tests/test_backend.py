class IdentityTests(object):
    def test_authenticate_bad_user(self):
        self.assertRaises(AssertionError,
                          self.identity_api.authenticate,
                          user_id=self.user_foo['id'] + 'WRONG',
                          tenant_id=self.tenant_bar['id'],
                          password=self.user_foo['password'])

    def test_authenticate_bad_password(self):
        self.assertRaises(AssertionError,
                          self.identity_api.authenticate,
                          user_id=self.user_foo['id'],
                          tenant_id=self.tenant_bar['id'],
                          password=self.user_foo['password'] + 'WRONG')

    def test_authenticate_invalid_tenant(self):
        self.assertRaises(AssertionError,
                          self.identity_api.authenticate,
                          user_id=self.user_foo['id'],
                          tenant_id=self.tenant_bar['id'] + 'WRONG',
                          password=self.user_foo['password'])

    def test_authenticate_no_tenant(self):
        user_ref, tenant_ref, metadata_ref = self.identity_api.authenticate(
                user_id=self.user_foo['id'],
                password=self.user_foo['password'])
        # NOTE(termie): the password field is left in user_foo to make it easier
        #               to authenticate in tests, but should not be returned by
        #               the api
        self.user_foo.pop('password')
        self.assertDictEquals(user_ref, self.user_foo)
        self.assert_(tenant_ref is None)
        self.assert_(not metadata_ref)

    def test_authenticate(self):
        user_ref, tenant_ref, metadata_ref = self.identity_api.authenticate(
                user_id=self.user_foo['id'],
                tenant_id=self.tenant_bar['id'],
                password=self.user_foo['password'])
        # NOTE(termie): the password field is left in user_foo to make it easier
        #               to authenticate in tests, but should not be returned by
        #               the api
        self.user_foo.pop('password')
        self.assertDictEquals(user_ref, self.user_foo)
        self.assertDictEquals(tenant_ref, self.tenant_bar)
        self.assertDictEquals(metadata_ref, self.metadata_foobar)

    def test_password_hashed(self):
        user_ref = self.identity_api._get_user(self.user_foo['id'])
        self.assertNotEqual(user_ref['password'], self.user_foo['password'])


    def test_get_tenant_bad_tenant(self):
        tenant_ref = self.identity_api.get_tenant(
                tenant_id=self.tenant_bar['id'] + 'WRONG')
        self.assert_(tenant_ref is None)

    def test_get_tenant(self):
        tenant_ref = self.identity_api.get_tenant(tenant_id=self.tenant_bar['id'])
        self.assertDictEquals(tenant_ref, self.tenant_bar)

    def test_get_tenant_by_name_bad_tenant(self):
        tenant_ref = self.identity_api.get_tenant(
                tenant_id=self.tenant_bar['name'] + 'WRONG')
        self.assert_(tenant_ref is None)

    def test_get_tenant_by_name(self):
        tenant_ref = self.identity_api.get_tenant_by_name(
                tenant_name=self.tenant_bar['name'])
        self.assertDictEquals(tenant_ref, self.tenant_bar)

    def test_get_user_bad_user(self):
        user_ref = self.identity_api.get_user(
                user_id=self.user_foo['id'] + 'WRONG')
        self.assert_(user_ref is None)

    def test_get_user(self):
        user_ref = self.identity_api.get_user(user_id=self.user_foo['id'])
        # NOTE(termie): the password field is left in user_foo to make it easier
        #               to authenticate in tests, but should not be returned by
        #               the api
        self.user_foo.pop('password')
        self.assertDictEquals(user_ref, self.user_foo)

    def test_get_metadata_bad_user(self):
        metadata_ref = self.identity_api.get_metadata(
                user_id=self.user_foo['id'] + 'WRONG',
                tenant_id=self.tenant_bar['id'])
        self.assert_(metadata_ref is None)

    def test_get_metadata_bad_tenant(self):
        metadata_ref = self.identity_api.get_metadata(
                user_id=self.user_foo['id'],
                tenant_id=self.tenant_bar['id'] + 'WRONG')
        self.assert_(metadata_ref is None)

    def test_get_metadata(self):
        metadata_ref = self.identity_api.get_metadata(
                user_id=self.user_foo['id'],
                tenant_id=self.tenant_bar['id'])
        self.assertDictEquals(metadata_ref, self.metadata_foobar)

    def test_get_role(self):
        role_ref = self.identity_api.get_role(
                role_id=self.role_keystone_admin['id'])
        self.assertDictEquals(role_ref, self.role_keystone_admin)

    def test_create_duplicate_user_id_fails(self):
        user = {'id': 'fake', 'name': 'fake1',
                'password': 'fakepass', 'tenants': ['bar',]}
        user_ref = self.identity_api.create_user('fake', user)
        user['name'] = 'fake2'
        try:
            self.assertRaises(Exception,
                              self.identity_api.create_user,
                              user['id'],
                              user)
        finally:
            user_ref = self.identity_api.delete_user('fake')

    def test_create_duplicate_user_name_fails(self):
        user = {'id': 'fake1', 'name': 'fake',
                'password': 'fakepass', 'tenants': ['bar',]}
        user_ref = self.identity_api.create_user('fake1', user)
        user['id'] = 'fake2'
        try:
            self.assertRaises(Exception,
                              self.identity_api.create_user,
                              user['id'],
                              user)
        finally:
            self.identity_api.delete_user('fake1')

    def test_create_duplicate_tenant_id_fails(self):
        tenant = {'id': 'fake', 'name': 'fake1'}
        tenant_ref = self.identity_api.create_tenant('fake', tenant)
        tenant['name'] = 'fake2'
        try:
            self.assertRaises(Exception,
                              self.identity_api.create_tenant,
                              tenant['id'],
                              tenant)
        finally:
            tenant_ref = self.identity_api.delete_tenant('fake')

    def test_create_duplicate_tenant_name_fails(self):
        tenant = {'id': 'fake1', 'name': 'fake'}
        tenant_ref = self.identity_api.create_tenant('fake1', tenant)
        tenant['id'] = 'fake2'
        try:
            self.assertRaises(Exception,
                              self.identity_api.create_tenant,
                              tenant['id'],
                              tenant)
        finally:
            self.identity_api.delete_tenant('fake1')
