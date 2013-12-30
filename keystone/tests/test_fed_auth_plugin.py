# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack Foundation
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
import uuid
import datetime


from keystone import tests
from keystone import token
from keystone import auth
from keystone import exception
from keystone import catalog

from keystone.tests import test_v3

class TestFedAuthPlugin(tests.TestCase):
    def setUp(self):
        super(TestFedAuthPlugin, self).setUp()
        self.config([
            tests.dirs.tests('test_fed_auth_plugin.conf')])
        self.load_backends()
        self.load_identity_providers()

        # need to register the token provider first because auth controller
        # depends on it
        token.provider.Manager()

        self.api = auth.controllers.Auth()

    def test_federated_discovery(self):

        # test correct response
        auth_data = {'methods': ['federated']}
        auth_data['federated'] = {
            'phase': 'discovery'}
        auth_data = {'identity': auth_data}
        auth_info = auth.controllers.AuthInfo.create(None, auth_data)
        auth_context = {'extras': {}, 'method_names': []}
        self.assertRaises(exception.AdditionalAuthRequired, self.api.authenticate,
                     {'environment': {}},
                     auth_info,
                     auth_context)

    def test_federated_missing_provider_request(self):

        # test NotFound exception is thrown
        auth_data = {'methods': ['federated']}
        auth_data['federated'] = {
            'phase': 'request'}
        auth_data = {'identity': auth_data}
        auth_info = auth.controllers.AuthInfo.create(None, auth_data)
        auth_context = {'extras': {}, 'method_names': []}
        self.assertRaises(exception.NotFound, self.api.authenticate,
                     {'environment': {}},
                     auth_info,
                     auth_context)

    def test_federated_apache2_request(self):

        # test correct response
        auth_data = {'methods': ['federated']}
        auth_data['federated'] = {
            'phase': 'request', 'provider_id': self.service['id']}
        auth_data = {'identity': auth_data}
        auth_info = auth.controllers.AuthInfo.create(None, auth_data)
        auth_context = {'extras': {}, 'method_names': []}
        self.assertRaises(exception.NotImplemented, self.api.authenticate,
                     {'environment': {}},
                     auth_info,
                     auth_context)

    def test_federated_missing_provider_validate(self):

        # test NotFound exception is thrown
        auth_data = {'methods': ['federated']}
        auth_data['federated'] = {
            'phase': 'validate'}
        auth_data = {'identity': auth_data}
        auth_info = auth.controllers.AuthInfo.create(None, auth_data)
        auth_context = {'extras': {}, 'method_names': []}
        self.assertRaises(exception.NotFound, self.api.authenticate,
                     {'environment': {}},
                     auth_info,
                     auth_context)

    def test_federated_apache2_validate(self):
        # test correct response
        auth_data = {'methods': ['federated']}
        attributes = []
        idp1_attribute = {'provider': self.service['id'], 'attributes':[{'uid':['Fred']}]}
        attributes.append(idp1_attribute)
        auth_data['federated'] = {
            'phase': 'validate', 'provider_id': self.service['id'],
            'protocol_data': {'uid': 'Fred', 'validity_time': datetime.datetime.now().time(),
            'user_identity': attributes}}
        auth_data = {'identity': auth_data}
        auth_info = auth.controllers.AuthInfo.create(None, auth_data)
        auth_context = {'extras': {}, 'method_names': []}
        self.api.authenticate({'environment': {}},
                     auth_info,
                     auth_context)

    def load_identity_providers(self):
        self.catalog_api = catalog.Manager()
        self.service = {'id':uuid.uuid4().hex,'name': 'apache_idp', 'type': 'idp.apache2'}
        self.catalog_api.create_service(self.service['id'], self.service)
