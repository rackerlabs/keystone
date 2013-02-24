import uuid

from keystone.common.sql import util as sql_util
from keystone import auth
from keystone import test
from keystone import config

import test_content_types


CONF = config.CONF


class RestfulTestCase(test_content_types.RestfulTestCase):
    def setUp(self, load_sample_data=True):
        """Setup for v3 Restful Test Cases.

        If a child class wants to create their own sample data
        and provide their own auth data to obtain tokens, then
        load_sample_data should be set to false.

        """
        self.config([
            test.etcdir('keystone.conf.sample'),
            test.testsdir('test_overrides.conf'),
            test.testsdir('backend_sql.conf'),
            test.testsdir('backend_sql_disk.conf')])
        sql_util.setup_test_database()
        self.load_backends()

        if load_sample_data:
            self.domain_id = uuid.uuid4().hex
            self.domain = self.new_domain_ref()
            self.domain['id'] = self.domain_id
            self.identity_api.create_domain(self.domain_id, self.domain)

            self.project_id = uuid.uuid4().hex
            self.project = self.new_project_ref(
                domain_id=self.domain_id)
            self.project['id'] = self.project_id
            self.identity_api.create_project(self.project_id, self.project)

            self.user_id = uuid.uuid4().hex
            self.user = self.new_user_ref(
                domain_id=self.domain_id,
                project_id=self.project_id)
            self.user['id'] = self.user_id
            self.identity_api.create_user(self.user_id, self.user)

            # create & grant policy.json's default role for admin_required
            self.role_id = uuid.uuid4().hex
            self.role = self.new_role_ref()
            self.role['id'] = self.role_id
            self.role['name'] = 'admin'
            self.identity_api.create_role(self.role_id, self.role)
            self.identity_api.add_role_to_user_and_project(
                self.user_id, self.project_id, self.role_id)

        self.public_server = self.serveapp('keystone', name='main')
        self.admin_server = self.serveapp('keystone', name='admin')

    def tearDown(self):
        self.public_server.kill()
        self.admin_server.kill()
        self.public_server = None
        self.admin_server = None
        sql_util.teardown_test_database()
        # need to reset the plug-ins
        auth.controllers.AUTH_METHODS = {}

    def new_ref(self):
        """Populates a ref with attributes common to all API entities."""
        return {
            'id': uuid.uuid4().hex,
            'name': uuid.uuid4().hex,
            'description': uuid.uuid4().hex,
            'enabled': True}

    def new_service_ref(self):
        ref = self.new_ref()
        ref['type'] = uuid.uuid4().hex
        return ref

    def new_endpoint_ref(self, service_id):
        ref = self.new_ref()
        ref['interface'] = uuid.uuid4().hex[:8]
        ref['service_id'] = service_id
        ref['url'] = uuid.uuid4().hex
        return ref

    def new_domain_ref(self):
        ref = self.new_ref()
        return ref

    def new_project_ref(self, domain_id):
        ref = self.new_ref()
        ref['domain_id'] = domain_id
        return ref

    def new_user_ref(self, domain_id, project_id=None):
        ref = self.new_ref()
        ref['domain_id'] = domain_id
        ref['email'] = uuid.uuid4().hex
        ref['password'] = uuid.uuid4().hex
        if project_id:
            ref['project_id'] = project_id
        return ref

    def new_group_ref(self, domain_id):
        ref = self.new_ref()
        ref['domain_id'] = domain_id
        return ref

    def new_credential_ref(self, user_id, project_id=None):
        ref = self.new_ref()
        ref['user_id'] = user_id
        ref['blob'] = uuid.uuid4().hex
        ref['type'] = uuid.uuid4().hex
        if project_id:
            ref['project_id'] = project_id
        return ref

    def new_role_ref(self):
        ref = self.new_ref()
        return ref

    def new_policy_ref(self):
        ref = self.new_ref()
        ref['blob'] = uuid.uuid4().hex
        ref['type'] = uuid.uuid4().hex
        return ref

    def get_scoped_token(self):
        """Convenience method so that we can test authenticated requests."""
        r = self.admin_request(
            method='POST',
            path='/v3/auth/tokens',
            body={
                'authentication': {
                    'methods': ['password'],
                    'password': {
                        'user': {
                            'name': self.user['name'],
                            'password': self.user['password'],
                            'domain': {
                                'id': self.user['domain_id']
                            }
                        }
                    }
                },
                'scope': {
                    'project': {
                        'id': self.project['id'],
                    }
                }
            })
        return r.getheader('X-Subject-Token')

    def get_requested_token(self, auth):
        """Request the specific token we want."""

        r = self.admin_request(
            method='POST',
            path='/v3/auth/tokens',
            body=auth)
        return r.getheader('X-Subject-Token')

    def v3_request(self, path, **kwargs):
        # Check if the caller has passed in auth details for
        # use in requesting the token
        auth = kwargs.get('auth', None)
        if auth:
            kwargs.pop('auth')
            token = self.get_requested_token(auth)
        else:
            token = self.get_scoped_token()
        path = '/v3' + path
        return self.admin_request(
            path=path,
            token=token,
            **kwargs)

    def get(self, path, **kwargs):
        return self.v3_request(method='GET', path=path, **kwargs)

    def head(self, path, **kwargs):
        return self.v3_request(method='HEAD', path=path, **kwargs)

    def post(self, path, **kwargs):
        return self.v3_request(method='POST', path=path, **kwargs)

    def put(self, path, **kwargs):
        return self.v3_request(method='PUT', path=path, **kwargs)

    def patch(self, path, **kwargs):
        return self.v3_request(method='PATCH', path=path, **kwargs)

    def delete(self, path, **kwargs):
        return self.v3_request(method='DELETE', path=path, **kwargs)

    def assertValidErrorResponse(self, r):
        self.assertIsNotNone(r.body.get('error'))
        self.assertIsNotNone(r.body['error'].get('code'))
        self.assertIsNotNone(r.body['error'].get('title'))
        self.assertIsNotNone(r.body['error'].get('message'))
        self.assertEqual(r.body['error']['code'], r.status)

    def assertValidListResponse(self, resp, key, entity_validator, ref=None,
                                expected_length=None):
        """Make assertions common to all API list responses.

        If a reference is provided, it's ID will be searched for in the
        response, and asserted to be equal.

        """
        entities = resp.body.get(key)
        self.assertIsNotNone(entities)

        if expected_length is not None:
            self.assertEqual(len(entities), expected_length)
        elif ref is not None:
            # we're at least expecting the ref
            self.assertTrue(len(entities))

        # collections should have relational links
        self.assertIsNotNone(resp.body.get('links'))
        self.assertIn('previous', resp.body['links'])
        self.assertIn('self', resp.body['links'])
        self.assertIn('next', resp.body['links'])
        self.assertIn(CONF.public_endpoint % CONF, resp.body['links']['self'])

        for entity in entities:
            self.assertIsNotNone(entity)
            self.assertValidEntity(entity)
            entity_validator(entity)
        if ref:
            entity = [x for x in entities if x['id'] == ref['id']][0]
            self.assertValidEntity(entity, ref)
            entity_validator(entity, ref)
        return entities

    def assertValidResponse(self, resp, key, entity_validator, ref):
        """Make assertions common to all API responses."""
        entity = resp.body.get(key)
        self.assertIsNotNone(entity)
        self.assertValidEntity(entity, ref)
        entity_validator(entity, ref)
        return entity

    def assertValidEntity(self, entity, ref=None):
        """Make assertions common to all API entities.

        If a reference is provided, the entity will also be compared against
        the reference.
        """
        keys = ['name', 'description', 'enabled']

        for k in ['id'] + keys:
            msg = '%s unexpectedly None in %s' % (k, entity)
            self.assertIsNotNone(entity.get(k), msg)

        self.assertIsNotNone(entity.get('links'))
        self.assertIsNotNone(entity['links'].get('self'))
        self.assertIn(CONF.public_endpoint % CONF, entity['links']['self'])
        self.assertIn(entity['id'], entity['links']['self'])

        if ref:
            for k in keys:
                msg = '%s not equal: %s != %s' % (k, ref[k], entity[k])
                self.assertEquals(ref[k], entity[k])

        return entity

    def build_auth_scope(self, project_id=None, project_name=None,
                         project_domain_id=None, project_domain_name=None,
                         domain_id=None, domain_name=None):
        scope_data = {}
        if project_id or project_name:
            scope_data['project'] = {}
            if project_id:
                scope_data['project']['id'] = project_id
            else:
                scope_data['project']['name'] = project_name
                if project_domain_id or project_domain_name:
                    project_domain_json = {}
                    if project_domain_id:
                        project_domain_json['id'] = project_domain_id
                    else:
                        project_domain_json['name'] = project_domain_name
                    scope_data['project']['domain'] = project_domain_json
        if domain_id or domain_name:
            scope_data['domain'] = {}
            if domain_id:
                scope_data['domain']['id'] = domain_id
            else:
                scope_data['domain']['name'] = domain_name
        return scope_data

    def build_password_auth(self, user_id=None, username=None,
                            user_domain_id=None, user_domain_name=None,
                            password=None):
        password_data = {'user': {}}
        if user_id:
            password_data['user']['id'] = user_id
        else:
            password_data['user']['name'] = username
            if user_domain_id or user_domain_name:
                password_data['user']['domain'] = {}
                if user_domain_id:
                    password_data['user']['domain']['id'] = user_domain_id
                else:
                    password_data['user']['domain']['name'] = user_domain_name
        password_data['user']['password'] = password
        return password_data

    def build_token_auth(self, token):
        return {'id': token}

    def build_authentication_request(self, token=None, user_id=None,
                                     username=None, user_domain_id=None,
                                     user_domain_name=None, password=None,
                                     project_id=None, project_name=None,
                                     project_domain_id=None,
                                     project_domain_name=None,
                                     domain_id=None, domain_name=None):
        """Build auth dictionary.

        It will create an auth dictionary based on all the arguments
        that it receives.
        """
        auth_data = {}
        auth_data['authentication'] = {'methods': []}
        if token:
            auth_data['authentication']['methods'].append('token')
            auth_data['authentication']['token'] = self.build_token_auth(token)
        if user_id or username:
            auth_data['authentication']['methods'].append('password')
            auth_data['authentication']['password'] = self.build_password_auth(
                user_id, username, user_domain_id, user_domain_name, password)
        if project_id or project_name or domain_id or domain_name:
            auth_data['scope'] = self.build_auth_scope(project_id,
                                                       project_name,
                                                       project_domain_id,
                                                       project_domain_name,
                                                       domain_id,
                                                       domain_name)
        return auth_data


class VersionTestCase(RestfulTestCase):
    def test_get_version(self):
        pass
