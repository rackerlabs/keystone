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

import kerberos
import mock

from keystone import auth
from keystone import exception
from keystone import tests


class TestKerberosAuthPlugin(tests.SQLDriverOverrides, tests.TestCase):
    @mock.patch.object(kerberos, 'getServerPrincipalDetails', autospec=True)
    def setUp(self, mock_kerberos):
        super(TestKerberosAuthPlugin, self).setUp()
        mock_kerberos.return_value = 'HTTP\keystone.example.com'
        self.load_backends()
        self.load_fixtures(tests.default_fixtures)
        self.api = auth.controllers.Auth()

    @mock.patch.object(kerberos, 'authGSSServerInit', autospec=True)
    def test_kerberos_negotiate(self, mock_server_init):
        """Test a client that sends the appropiate method authentication
        the server should return Negotiate to the client to initiate the
        handshake
        """
        auth_data = {'methods': ['kerberos']}
        auth_data['kerberos'] = {}
        auth_data = {'identity': auth_data}
        auth_info = auth.controllers.AuthInfo.create(None, auth_data)
        auth_context = {'extras': {}, 'method_names': []}
        context = {'environment': {}, 'headers': {}}
        try:
            self.api.authenticate(context, auth_info, auth_context)
            # It should give an exception if not assert
            self.assertTrue(False)
        except exception.KerberosUnauthorized as e:
            self.assertFalse(mock_server_init.called)
            authHeader = dict(e.headers)['WWW-Authenticate']
            self.assertTrue('Negotiate' in authHeader)

    @mock.patch.object(kerberos, 'authGSSServerInit', autospec=True)
    @mock.patch.object(kerberos, 'authGSSServerStep', autospec=True)
    @mock.patch.object(kerberos, 'authGSSServerResponse', autospec=True)
    @mock.patch.object(kerberos, 'authGSSServerClean', autospec=True)
    def test_kerberos_authenticate_step(self,
                                        mock_server_clean,
                                        mock_server_response,
                                        mock_server_step,
                                        mock_server_init):
        """Test a step on the handshake mechanism, in this one the client
        sends a request to the server with the TGT and the library determines
        to do an extra step for authentication (mutual authentication)
        """
        auth_data = {'methods': ['kerberos']}
        auth_data['kerberos'] = {}
        auth_data = {'identity': auth_data}
        auth_info = auth.controllers.AuthInfo.create(None, auth_data)
        auth_context = {'extras': {}, 'method_names': []}
        context = {'environment': {}, 'headers': {}}
        context['headers'] = {'Authorization': 'Negotiate KRB-CLITOKEN'}

        mock_server_init.return_value = (kerberos.AUTH_GSS_COMPLETE, 'CTX')
        mock_server_step.return_value = (kerberos.AUTH_GSS_CONTINUE, 'CTX')
        mock_server_response.return_value = 'KRB-SRVTOKEN'

        # test correct response
        try:
            self.api.authenticate(context, auth_info, auth_context)
            # It should give an exception if not assert
            self.assertTrue(False)
        except exception.KerberosUnauthorized as e:
            self.assertTrue(mock_server_init.called)
            self.assertTrue(mock_server_step.called)
            self.assertTrue(mock_server_response.called)
            authHeader = dict(e.headers)['WWW-Authenticate']
            self.assertTrue('KRB-SRVTOKEN' in authHeader)

    @mock.patch.object(kerberos, 'authGSSServerInit', autospec=True)
    @mock.patch.object(kerberos, 'authGSSServerStep', autospec=True)
    @mock.patch.object(kerberos, 'authGSSServerResponse', autospec=True)
    @mock.patch.object(kerberos, 'authGSSServerUserName', autospec=True)
    @mock.patch.object(kerberos, 'authGSSServerClean', autospec=True)
    def test_kerberos_authenticate_complete(self,
                                            mock_server_clean,
                                            mock_server_username,
                                            mock_server_response,
                                            mock_server_step,
                                            mock_server_init):
        """Test a complete authentication with a client that sends a
        request to the server with the TGT and the library determines that
        it is authenticated
        """
        auth_data = {'methods': ['kerberos']}
        auth_data['kerberos'] = {}
        auth_data = {'identity': auth_data}
        auth_info = auth.controllers.AuthInfo.create(None, auth_data)
        auth_context = {'extras': {}, 'method_names': []}
        context = {'environment': {}, 'headers': {}}
        context['headers'] = {'Authorization': 'Negotiate KRB-CLITOKEN'}

        mock_server_init.return_value = (kerberos.AUTH_GSS_COMPLETE, 'CTX')
        mock_server_step.return_value = (kerberos.AUTH_GSS_COMPLETE, 'CTX')
        mock_server_response.return_value = 'KRB-SRVTOKEN'
        mock_server_username.return_value = "%s@%s" %\
            (self.user_foo['name'], self.domain_default['name'])

        self.api.authenticate(context, auth_info, auth_context)
        self.assertTrue(mock_server_init.called)
        self.assertTrue(mock_server_step.called)
        self.assertTrue(mock_server_response.called)
        self.assertTrue(mock_server_username.called)
        self.assertEqual('foo', auth_context['user_id'])

    @mock.patch.object(kerberos, 'authGSSServerInit', autospec=True)
    @mock.patch.object(kerberos, 'authGSSServerStep', autospec=True)
    @mock.patch.object(kerberos, 'authGSSServerResponse', autospec=True)
    @mock.patch.object(kerberos, 'authGSSServerUserName', autospec=True)
    @mock.patch.object(kerberos, 'authGSSServerClean', autospec=True)
    def test_kerberos_authenticate_user_404(self,
                                            mock_server_clean,
                                            mock_server_username,
                                            mock_server_response,
                                            mock_server_step,
                                            mock_server_init):
        """Test for a complete kerberos authentication in this case the
        client has a valid kerberos token but it the user it refers does not
        exist on the keystone service
        """
        auth_data = {'methods': ['kerberos']}
        auth_data['kerberos'] = {}
        auth_data = {'identity': auth_data}
        auth_info = auth.controllers.AuthInfo.create(None, auth_data)
        auth_context = {'extras': {}, 'method_names': []}
        context = {'environment': {}, 'headers': {}}
        context['headers'] = {'Authorization': 'Negotiate KRB-CLITOKEN'}

        mock_server_init.return_value = (kerberos.AUTH_GSS_COMPLETE, 'CTX')
        mock_server_step.return_value = (kerberos.AUTH_GSS_COMPLETE, 'CTX')
        mock_server_response.return_value = 'KRB-SRVTOKEN'
        mock_server_username.return_value = "%s@%s" %\
            (uuid.uuid4().hex, self.domain_default['name'])

        self.assertRaises(exception.UserNotFound,
                          self.api.authenticate,
                          context,
                          auth_info,
                          auth_context)
        self.assertTrue(mock_server_init.called)
        self.assertTrue(mock_server_step.called)
        self.assertTrue(mock_server_response.called)
        self.assertTrue(mock_server_username.called)

    @mock.patch.object(kerberos, 'authGSSServerInit', autospec=True)
    @mock.patch.object(kerberos, 'authGSSServerStep', autospec=True)
    @mock.patch.object(kerberos, 'authGSSServerResponse', autospec=True)
    @mock.patch.object(kerberos, 'authGSSServerUserName', autospec=True)
    @mock.patch.object(kerberos, 'authGSSServerClean', autospec=True)
    def test_kerberos_authenticate_domain_404(self,
                                              mock_server_clean,
                                              mock_server_username,
                                              mock_server_response,
                                              mock_server_step,
                                              mock_server_init):
        """Test for a complete kerberos authentication in this case the
        client has a valid kerberos token but the domain it refers does not
        exist on the keystone service
        """
        auth_data = {'methods': ['kerberos']}
        auth_data['kerberos'] = {}
        auth_data = {'identity': auth_data}
        auth_info = auth.controllers.AuthInfo.create(None, auth_data)
        auth_context = {'extras': {}, 'method_names': []}
        context = {'environment': {}, 'headers': {}}
        context['headers'] = {'Authorization': 'Negotiate KRB-CLITOKEN'}

        mock_server_init.return_value = (kerberos.AUTH_GSS_COMPLETE, 'CTX')
        mock_server_step.return_value = (kerberos.AUTH_GSS_COMPLETE, 'CTX')
        mock_server_response.return_value = 'KRB-SRVTOKEN'
        mock_server_username.return_value = "%s@%s" %\
            (self.user_foo['name'], uuid.uuid4().hex)

        mock_server_username.return_value = 'FOO@NOTFOUND'
        self.assertRaises(exception.DomainNotFound,
                          self.api.authenticate,
                          context,
                          auth_info,
                          auth_context)
        self.assertTrue(mock_server_init.called)
        self.assertTrue(mock_server_step.called)
        self.assertTrue(mock_server_response.called)
        self.assertTrue(mock_server_username.called)

    @mock.patch.object(kerberos, 'authGSSServerInit', autospec=True)
    @mock.patch.object(kerberos, 'authGSSServerStep', autospec=True)
    @mock.patch.object(kerberos, 'authGSSServerResponse', autospec=True)
    @mock.patch.object(kerberos, 'authGSSServerUserName', autospec=True)
    @mock.patch.object(kerberos, 'authGSSServerClean', autospec=True)
    def test_kerberos_authenticate_503(self,
                                       mock_server_clean,
                                       mock_server_username,
                                       mock_server_response,
                                       mock_server_step,
                                       mock_server_init):
        """Test with a failure on the kerberos library that is unable
        to obtain a server token to send to the client
        """
        auth_data = {'methods': ['kerberos']}
        auth_data['kerberos'] = {}
        auth_data = {'identity': auth_data}
        auth_info = auth.controllers.AuthInfo.create(None, auth_data)
        auth_context = {'extras': {}, 'method_names': []}
        context = {'environment': {}, 'headers': {}}
        context['headers'] = {'Authorization': 'Negotiate KRB-CLITOKEN'}

        mock_server_init.return_value = (kerberos.AUTH_GSS_COMPLETE, 'CTX')
        mock_server_step.return_value = (kerberos.AUTH_GSS_CONTINUE, 'CTX')
        mock_server_response.return_value = None
        mock_server_username.return_value = "%s@%s" %\
            (self.user_foo['name'], self.domain_default['name'])

        self.assertRaises(exception.Forbidden,
                          self.api.authenticate,
                          context,
                          auth_info,
                          auth_context)
        self.assertTrue(mock_server_init.called)
        self.assertTrue(mock_server_step.called)
        self.assertTrue(mock_server_response.called)
