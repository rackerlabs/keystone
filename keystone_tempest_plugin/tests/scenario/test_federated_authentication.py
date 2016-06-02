# Copyright 2016 Red Hat, Inc.
#
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

from lxml import etree

from tempest import config
from tempest.lib.common.utils import data_utils

from keystone_tempest_plugin.tests import base


CONF = config.CONF


class TestSaml2EcpFederatedAuthentication(base.BaseIdentityTest):

    HTTP_MOVED_TEMPORARILY = 302

    HTTP_SEE_OTHER = 303

    ECP_SAML2_NAMESPACES = {
        'ecp': 'urn:oasis:names:tc:SAML:2.0:profiles:SSO:ecp',
        'S': 'http://schemas.xmlsoap.org/soap/envelope/',
        'paos': 'urn:liberty:paos:2003-08'
    }

    ECP_SERVICE_PROVIDER_CONSUMER_URL = ('/S:Envelope/S:Header/paos:Request/'
                                         '@responseConsumerURL')

    ECP_IDP_CONSUMER_URL = ('/S:Envelope/S:Header/ecp:Response/'
                            '@AssertionConsumerServiceURL')

    ECP_RELAY_STATE = '//ecp:RelayState'

    def _setup_idp(self):
        self.idp_id = CONF.fed_scenario.idp_id
        remote_ids = CONF.fed_scenario.idp_remote_ids
        self.idps_client.create_identity_provider(
            self.idp_id, remote_ids=remote_ids, enabled=True)
        self.addCleanup(
            self.idps_client.delete_identity_provider, self.idp_id)

    def _setup_mapping(self):
        self.mapping_id = data_utils.rand_uuid_hex()
        mapping_remote_type = CONF.fed_scenario.mapping_remote_type
        mapping_user_id = CONF.fed_scenario.mapping_user_id
        mapping_group_id = CONF.fed_scenario.mapping_group_id

        rules = [{
            'local': [
                {
                    'user': {'id': mapping_user_id}
                },
                {
                    'group': {'id': mapping_group_id}
                }
            ],
            'remote': [
                {
                    'type': mapping_remote_type
                }
            ]
        }]
        mapping_ref = {'rules': rules}
        self.mappings_client.create_mapping_rule(self.mapping_id, mapping_ref)
        self.addCleanup(
            self.mappings_client.delete_mapping_rule, self.mapping_id)

    def _setup_protocol(self):
        self.protocol_id = CONF.fed_scenario.protocol_id
        self.idps_client.add_protocol_and_mapping(
            self.idp_id, self.protocol_id, self.mapping_id)
        self.addCleanup(
            self.idps_client.delete_protocol_and_mapping, self.idp_id, self.protocol_id)

    def setUp(self):
        super(TestSaml2EcpFederatedAuthentication, self).setUp()
        self.keystone_v3_endpoint = CONF.identity.uri_v3
        self.idp_url = CONF.fed_scenario.idp_ecp_url
        self.username = CONF.fed_scenario.idp_username
        self.password = CONF.fed_scenario.idp_password

        # Reset client's session to avoid getting garbage from another runs
        self.saml2_client.reset_session()

        # Setup identity provider, mapping and protocol
        self._setup_idp()
        self._setup_mapping()
        self._setup_protocol()

    def _assert_consumer_url(self, saml2_authn_request, idp_authn_response):
        sp_consumer_url = saml2_authn_request.xpath(
            self.ECP_SERVICE_PROVIDER_CONSUMER_URL,
            namespaces=self.ECP_SAML2_NAMESPACES)
        self.assertEqual(1, len(sp_consumer_url))

        idp_consumer_url = idp_authn_response.xpath(
            self.ECP_IDP_CONSUMER_URL,
            namespaces=self.ECP_SAML2_NAMESPACES)
        self.assertEqual(1, len(idp_consumer_url))

        self.assertEqual(sp_consumer_url[0], idp_consumer_url[0])
        return idp_consumer_url[0]

    def _request_unscoped_token(self):
        resp = self.saml2_client.send_service_provider_request(
            self.keystone_v3_endpoint, self.idp_id, self.protocol_id)
        self.assertEqual(200, resp.status_code)
        saml2_authn_request = etree.XML(resp.content)

        resp = self.saml2_client.send_identity_provider_authn_request(
            saml2_authn_request, self.idp_url, self.username, self.password)
        self.assertEqual(200, resp.status_code)
        saml2_idp_authn_response = etree.XML(resp.content)

        # Assert that both saml2_authn_request and saml2_idp_authn_response
        # have the same consumer URL.
        idp_consumer_url = self._assert_consumer_url(
            saml2_authn_request, saml2_idp_authn_response)

        relay_state = saml2_authn_request.xpath(
            self.ECP_RELAY_STATE, namespaces=self.ECP_SAML2_NAMESPACES)[0]

        resp = self.saml2_client.send_service_provider_saml2_authn_response(
            saml2_idp_authn_response, relay_state, idp_consumer_url)
        # Must receive a redirect from service provider
        self.assertIn(resp.status_code,
                      [self.HTTP_MOVED_TEMPORARILY, self.HTTP_SEE_OTHER])

        sp_url = resp.headers['location']
        resp = (
            self.saml2_client.send_service_provider_unscoped_token_request(
                sp_url))
        # We can receive multiple types of errors here, the response depends on
        # the mapping and the username used to authenticate in the identity
        # provider and also in the Identity Provider remote ID validation.
        # If everything works well, we receive an unscoped token.
        self.assertEqual(201, resp.status_code)
        self.assertIn('X-Subject-Token', resp.headers)
        self.assertNotEmpty(resp.json())

        return resp

    def test_request_unscoped_token(self):
        self._request_unscoped_token()

    def test_request_scoped_token(self):
        resp = self._request_unscoped_token()
        token_id = resp.headers['X-Subject-Token']

        projects = self.auth_client.get_available_projects_scopes(
            self.keystone_v3_endpoint, token_id)['projects']
        self.assertNotEmpty(projects)

        # Get a scoped token to one of the listed projects
        self.tokens_client.auth(
            project_id=projects[0]['id'], token=token_id)
