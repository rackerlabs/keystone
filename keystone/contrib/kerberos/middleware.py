# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC
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

import kerberos
import os
import webob

from keystone.common import wsgi

from keystone.auth import controllers as auth_v3_controllers
from keystone.token import provider

from keystone.openstack.common import jsonutils
from keystone.openstack.common import log

LOG = log.getLogger(__name__)

# Environment variable used to pass the request context
CONTEXT_ENV = wsgi.CONTEXT_ENV


class KerberosAuthV3Middleware(wsgi.Middleware):
    token_provider = provider.Manager()

    def __init__(self, app, hostname, keytab):
        super(KerberosAuthV3Middleware, self).__init__(app)
        self.service = 'HTTP@%s' % hostname
        os.environ['KRB5_KTNAME'] = keytab
        try:
            principal = kerberos.getServerPrincipalDetails('HTTP', hostname)
        except kerberos.KrbError as exc:
            LOG.warn('KerberosAuthV3Middleware: %s' % exc.message[0])
        else:
            LOG.debug('KerberosAuthV3Middleware is identifying as %s'
                      % principal)

    def create_token(self, context, username, auth):
        context['REMOTE_USER'] = username
        context['query_string'] = 'nocatalog'
        return auth_v3_controllers.Auth().authenticate_for_token(context, auth)

    def authenticate(self, client_token):
        state = None
        server_token = None
        user = None
        try:
            rc, state = kerberos.authGSSServerInit(self.service)
            if rc == kerberos.AUTH_GSS_COMPLETE:
                rc = kerberos.authGSSServerStep(state, client_token)
                if rc == kerberos.AUTH_GSS_COMPLETE:
                    server_token = kerberos.authGSSServerResponse(state)
                    user = kerberos.authGSSServerUserName(state)
                elif rc == kerberos.AUTH_GSS_CONTINUE:
                    server_token = kerberos.authGSSServerResponse(state)
        except kerberos.GSSError:
            pass
        finally:
            if state:
                kerberos.authGSSServerClean(state)
        return server_token, user

    def unauthorized_response(self, token=None):
        response = webob.Response()
        response.status_code = 401
        if token:
            response.headers['WWW-Authenticate'] = token
        else:
            response.headers['WWW-Authenticate'] = 'Negotiate'
        return response

    def forbidden_response(self):
        response = webob.Response()
        response.status_code = 403
        return response

    def process_request(self, request):
        auth_body = jsonutils.loads(request.body)['auth']
        if 'kerberos' in auth_body['identity']['methods']:
            context = request.environ.get(CONTEXT_ENV, {})
            response = None
            authHeader = request.environ.get('HTTP_AUTHORIZATION')
            if authHeader is None:
                return self.unauthorized_response()

            client_token = ''.join(authHeader.split()[1:])
            server_token, user = self.authenticate(client_token)

            if user:
                auth_body['identity']['methods'] = [
                    m for m in auth_body['identity']['methods']
                    if m != 'kerberos']
                response = self.create_token(context, user, auth_body)
                response.headers['WWW-Authenticate'] = server_token
                return response
            elif server_token:
                return self.unauthorized_response(server_token)
            else:
                return self.forbidden_response()
