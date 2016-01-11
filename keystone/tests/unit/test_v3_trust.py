# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import datetime
import uuid

from oslo_config import cfg
from six.moves import http_client

from keystone.tests import unit
from keystone.tests.unit import test_v3

CONF = cfg.CONF


class TestTrustOperations(test_v3.RestfulTestCase):

    def config_overrides(self):
        super(TestTrustOperations, self).config_overrides()
        self.config_fixture.config(group='revoke', driver='kvs')
        self.config_fixture.config(
            group='token',
            provider='pki',
            revoke_by_id=False)
        self.config_fixture.config(group='trust', enabled=True)

    def setUp(self):
        super(TestTrustOperations, self).setUp()

        # create a trustee to delegate stuff to
        self.trustee_user = unit.create_user(self.identity_api,
                                             domain_id=self.domain_id)
        self.trustee_user_id = self.trustee_user['id']

    def test_create_trust_bad_request(self):
        # The server returns a 403 Forbidden rather than a 400 Bad Request, see
        # bug 1133435
        self.post('/OS-TRUST/trusts', body={'trust': {}},
                  expected_status=http_client.FORBIDDEN)

    def test_list_trusts(self):
        ref = unit.new_trust_ref(
            trustor_user_id=self.user_id,
            trustee_user_id=self.trustee_user_id,
            project_id=self.project_id,
            impersonation=False,
            expires=dict(minutes=1),
            role_ids=[self.role_id])

        for i in range(3):
            ref['expires_at'] = datetime.datetime.utcnow().replace(
                year=2031).strftime(unit.TIME_FORMAT)
            r = self.post('/OS-TRUST/trusts', body={'trust': ref})
            self.assertValidTrustResponse(r, ref)

        r = self.get('/OS-TRUST/trusts')
        trusts = r.result['trusts']
        self.assertEqual(3, len(trusts))
        self.assertValidTrustListResponse(r)

        r = self.get('/OS-TRUST/trusts?trustor_user_id=%s' %
                     self.user_id)
        trusts = r.result['trusts']
        self.assertEqual(3, len(trusts))
        self.assertValidTrustListResponse(r)

        r = self.get('/OS-TRUST/trusts?trustee_user_id=%s' %
                     self.user_id)
        trusts = r.result['trusts']
        self.assertEqual(0, len(trusts))

    def test_delete_trust(self):
        ref = unit.new_trust_ref(
            trustor_user_id=self.user_id,
            trustee_user_id=self.trustee_user_id,
            project_id=self.project_id,
            impersonation=False,
            expires=dict(minutes=1),
            role_ids=[self.role_id])

        r = self.post('/OS-TRUST/trusts', body={'trust': ref})

        trust = self.assertValidTrustResponse(r, ref)

        self.delete('/OS-TRUST/trusts/%(trust_id)s' % {
            'trust_id': trust['id']})

        self.get('/OS-TRUST/trusts/%(trust_id)s' % {
            'trust_id': trust['id']},
            expected_status=http_client.NOT_FOUND)

    def test_invalid_trust_request_without_trustee(self):
        ref = unit.new_trust_ref(
            trustor_user_id=self.user_id,
            trustee_user_id=self.trustee_user_id,
            project_id=self.project_id,
            role_ids=[self.role_id])

        del ref['trustee_user_id']

        self.post('/OS-TRUST/trusts',
                  body={'trust': ref},
                  expected_status=http_client.BAD_REQUEST)

    def test_invalid_trust_request_without_impersonation(self):
        ref = unit.new_trust_ref(
            trustor_user_id=self.user_id,
            trustee_user_id=self.trustee_user_id,
            project_id=self.project_id,
            role_ids=[self.role_id])

        del ref['impersonation']

        self.post('/OS-TRUST/trusts',
                  body={'trust': ref},
                  expected_status=http_client.BAD_REQUEST)

    def test_create_trust_with_bad_values_for_remaining_uses(self):
        # negative values for the remaining_uses parameter are forbidden
        self._create_trust_with_bad_remaining_use(bad_value=-1)
        # 0 is a forbidden value as well
        self._create_trust_with_bad_remaining_use(bad_value=0)
        # as are non integer values
        self._create_trust_with_bad_remaining_use(bad_value="a bad value")
        self._create_trust_with_bad_remaining_use(bad_value=7.2)

    def _create_trust_with_bad_remaining_use(self, bad_value):
        ref = unit.new_trust_ref(
            trustor_user_id=self.user_id,
            trustee_user_id=self.trustee_user_id,
            project_id=self.project_id,
            remaining_uses=bad_value,
            role_ids=[self.role_id])
        self.post('/OS-TRUST/trusts',
                  body={'trust': ref},
                  expected_status=http_client.BAD_REQUEST)

    # test create trust
    # test get trust
    # test trust cannot be updated
    # test delete trust

    def test_trust_crud(self):
        ref = unit.new_trust_ref(
            trustor_user_id=self.user_id,
            trustee_user_id=self.trustee_user_id,
            project_id=self.project_id,
            role_ids=[self.role_id])
        r = self.post('/OS-TRUST/trusts', body={'trust': ref})
        trust = self.assertValidTrustResponse(r, ref)

        r = self.get(
            '/OS-TRUST/trusts/%(trust_id)s' % {'trust_id': trust['id']})
        self.assertValidTrustResponse(r, ref)

        # validate roles on the trust
        r = self.get(
            '/OS-TRUST/trusts/%(trust_id)s/roles' % {
                'trust_id': trust['id']})
        roles = self.assertValidRoleListResponse(r, self.role)
        self.assertIn(self.role['id'], [x['id'] for x in roles])
        self.head(
            '/OS-TRUST/trusts/%(trust_id)s/roles/%(role_id)s' % {
                'trust_id': trust['id'],
                'role_id': self.role['id']},
            expected_status=http_client.OK)
        r = self.get(
            '/OS-TRUST/trusts/%(trust_id)s/roles/%(role_id)s' % {
                'trust_id': trust['id'],
                'role_id': self.role['id']})
        self.assertValidRoleResponse(r, self.role)

        r = self.get('/OS-TRUST/trusts')
        self.assertValidTrustListResponse(r, trust)

        # trusts are immutable
        self.patch(
            '/OS-TRUST/trusts/%(trust_id)s' % {'trust_id': trust['id']},
            body={'trust': ref},
            expected_status=http_client.NOT_FOUND)

        self.delete(
            '/OS-TRUST/trusts/%(trust_id)s' % {'trust_id': trust['id']})

        self.get(
            '/OS-TRUST/trusts/%(trust_id)s' % {'trust_id': trust['id']},
            expected_status=http_client.NOT_FOUND)

    def test_create_trust_trustee_returns_not_found(self):
        ref = unit.new_trust_ref(
            trustor_user_id=self.user_id,
            trustee_user_id=uuid.uuid4().hex,
            project_id=self.project_id,
            role_ids=[self.role_id])
        self.post('/OS-TRUST/trusts', body={'trust': ref},
                  expected_status=http_client.NOT_FOUND)

    def test_create_trust_trustor_trustee_backwards(self):
        ref = unit.new_trust_ref(
            trustor_user_id=self.trustee_user_id,
            trustee_user_id=self.user_id,
            project_id=self.project_id,
            role_ids=[self.role_id])
        self.post('/OS-TRUST/trusts', body={'trust': ref},
                  expected_status=http_client.FORBIDDEN)

    def test_create_trust_project_returns_not_found(self):
        ref = unit.new_trust_ref(
            trustor_user_id=self.user_id,
            trustee_user_id=self.trustee_user_id,
            project_id=uuid.uuid4().hex,
            role_ids=[self.role_id])
        self.post('/OS-TRUST/trusts', body={'trust': ref},
                  expected_status=http_client.NOT_FOUND)

    def test_create_trust_role_id_returns_not_found(self):
        ref = unit.new_trust_ref(
            trustor_user_id=self.user_id,
            trustee_user_id=self.trustee_user_id,
            project_id=self.project_id,
            role_ids=[uuid.uuid4().hex])
        self.post('/OS-TRUST/trusts', body={'trust': ref},
                  expected_status=http_client.NOT_FOUND)

    def test_create_trust_role_name_returns_not_found(self):
        ref = unit.new_trust_ref(
            trustor_user_id=self.user_id,
            trustee_user_id=self.trustee_user_id,
            project_id=self.project_id,
            role_names=[uuid.uuid4().hex])
        self.post('/OS-TRUST/trusts', body={'trust': ref},
                  expected_status=http_client.NOT_FOUND)

    def test_v3_v2_intermix_trustor_not_in_default_domain_failed(self):
        ref = unit.new_trust_ref(
            trustor_user_id=self.user_id,
            trustee_user_id=self.default_domain_user_id,
            project_id=self.project_id,
            impersonation=False,
            expires=dict(minutes=1),
            role_ids=[self.role_id])

        r = self.post('/OS-TRUST/trusts', body={'trust': ref})
        trust = self.assertValidTrustResponse(r)

        auth_data = self.build_authentication_request(
            user_id=self.default_domain_user['id'],
            password=self.default_domain_user['password'],
            trust_id=trust['id'])
        r = self.v3_create_token(auth_data)
        self.assertValidProjectTrustScopedTokenResponse(
            r, self.default_domain_user)

        token = r.headers.get('X-Subject-Token')

        # now validate the v3 token with v2 API
        path = '/v2.0/tokens/%s' % (token)
        self.admin_request(
            path=path, token=CONF.admin_token,
            method='GET', expected_status=http_client.UNAUTHORIZED)

    def test_v3_v2_intermix_trustor_not_in_default_domaini_failed(self):
        ref = unit.new_trust_ref(
            trustor_user_id=self.default_domain_user_id,
            trustee_user_id=self.trustee_user_id,
            project_id=self.default_domain_project_id,
            impersonation=False,
            expires=dict(minutes=1),
            role_ids=[self.role_id])

        auth_data = self.build_authentication_request(
            user_id=self.default_domain_user['id'],
            password=self.default_domain_user['password'],
            project_id=self.default_domain_project_id)
        token = self.get_requested_token(auth_data)

        r = self.post('/OS-TRUST/trusts', body={'trust': ref}, token=token)
        trust = self.assertValidTrustResponse(r)

        auth_data = self.build_authentication_request(
            user_id=self.trustee_user['id'],
            password=self.trustee_user['password'],
            trust_id=trust['id'])
        r = self.v3_create_token(auth_data)
        self.assertValidProjectTrustScopedTokenResponse(
            r, self.trustee_user)
        token = r.headers.get('X-Subject-Token')

        # now validate the v3 token with v2 API
        path = '/v2.0/tokens/%s' % (token)
        self.admin_request(
            path=path, token=CONF.admin_token,
            method='GET', expected_status=http_client.UNAUTHORIZED)

    def test_v3_v2_intermix_project_not_in_default_domaini_failed(self):
        # create a trustee in default domain to delegate stuff to
        trustee_user = unit.create_user(self.identity_api,
                                        domain_id=test_v3.DEFAULT_DOMAIN_ID)
        trustee_user_id = trustee_user['id']

        ref = unit.new_trust_ref(
            trustor_user_id=self.default_domain_user_id,
            trustee_user_id=trustee_user_id,
            project_id=self.project_id,
            impersonation=False,
            expires=dict(minutes=1),
            role_ids=[self.role_id])

        auth_data = self.build_authentication_request(
            user_id=self.default_domain_user['id'],
            password=self.default_domain_user['password'],
            project_id=self.default_domain_project_id)
        token = self.get_requested_token(auth_data)

        r = self.post('/OS-TRUST/trusts', body={'trust': ref}, token=token)
        trust = self.assertValidTrustResponse(r)

        auth_data = self.build_authentication_request(
            user_id=trustee_user['id'],
            password=trustee_user['password'],
            trust_id=trust['id'])
        r = self.v3_create_token(auth_data)
        self.assertValidProjectTrustScopedTokenResponse(
            r, trustee_user)
        token = r.headers.get('X-Subject-Token')

        # now validate the v3 token with v2 API
        path = '/v2.0/tokens/%s' % (token)
        self.admin_request(
            path=path, token=CONF.admin_token,
            method='GET', expected_status=http_client.UNAUTHORIZED)

    def test_v3_v2_intermix(self):
        # create a trustee in default domain to delegate stuff to
        trustee_user = unit.create_user(self.identity_api,
                                        domain_id=test_v3.DEFAULT_DOMAIN_ID)
        trustee_user_id = trustee_user['id']

        ref = unit.new_trust_ref(
            trustor_user_id=self.default_domain_user_id,
            trustee_user_id=trustee_user_id,
            project_id=self.default_domain_project_id,
            impersonation=False,
            expires=dict(minutes=1),
            role_ids=[self.role_id])
        auth_data = self.build_authentication_request(
            user_id=self.default_domain_user['id'],
            password=self.default_domain_user['password'],
            project_id=self.default_domain_project_id)
        token = self.get_requested_token(auth_data)

        r = self.post('/OS-TRUST/trusts', body={'trust': ref}, token=token)
        trust = self.assertValidTrustResponse(r)

        auth_data = self.build_authentication_request(
            user_id=trustee_user['id'],
            password=trustee_user['password'],
            trust_id=trust['id'])
        r = self.v3_create_token(auth_data)
        self.assertValidProjectTrustScopedTokenResponse(
            r, trustee_user)
        token = r.headers.get('X-Subject-Token')

        # now validate the v3 token with v2 API
        path = '/v2.0/tokens/%s' % (token)
        self.admin_request(
            path=path, token=CONF.admin_token,
            method='GET', expected_status=http_client.OK)

    def test_exercise_trust_scoped_token_without_impersonation(self):
        ref = unit.new_trust_ref(
            trustor_user_id=self.user_id,
            trustee_user_id=self.trustee_user_id,
            project_id=self.project_id,
            impersonation=False,
            expires=dict(minutes=1),
            role_ids=[self.role_id])

        r = self.post('/OS-TRUST/trusts', body={'trust': ref})
        trust = self.assertValidTrustResponse(r)

        auth_data = self.build_authentication_request(
            user_id=self.trustee_user['id'],
            password=self.trustee_user['password'],
            trust_id=trust['id'])
        r = self.v3_create_token(auth_data)
        self.assertValidProjectTrustScopedTokenResponse(r, self.trustee_user)
        self.assertEqual(self.trustee_user['id'],
                         r.result['token']['user']['id'])
        self.assertEqual(self.trustee_user['name'],
                         r.result['token']['user']['name'])
        self.assertEqual(self.domain['id'],
                         r.result['token']['user']['domain']['id'])
        self.assertEqual(self.domain['name'],
                         r.result['token']['user']['domain']['name'])
        self.assertEqual(self.project['id'],
                         r.result['token']['project']['id'])
        self.assertEqual(self.project['name'],
                         r.result['token']['project']['name'])

    def test_exercise_trust_scoped_token_with_impersonation(self):
        ref = unit.new_trust_ref(
            trustor_user_id=self.user_id,
            trustee_user_id=self.trustee_user_id,
            project_id=self.project_id,
            impersonation=True,
            expires=dict(minutes=1),
            role_ids=[self.role_id])

        r = self.post('/OS-TRUST/trusts', body={'trust': ref})
        trust = self.assertValidTrustResponse(r)

        auth_data = self.build_authentication_request(
            user_id=self.trustee_user['id'],
            password=self.trustee_user['password'],
            trust_id=trust['id'])
        r = self.v3_create_token(auth_data)
        self.assertValidProjectTrustScopedTokenResponse(r, self.user)
        self.assertEqual(self.user['id'], r.result['token']['user']['id'])
        self.assertEqual(self.user['name'], r.result['token']['user']['name'])
        self.assertEqual(self.domain['id'],
                         r.result['token']['user']['domain']['id'])
        self.assertEqual(self.domain['name'],
                         r.result['token']['user']['domain']['name'])
        self.assertEqual(self.project['id'],
                         r.result['token']['project']['id'])
        self.assertEqual(self.project['name'],
                         r.result['token']['project']['name'])
