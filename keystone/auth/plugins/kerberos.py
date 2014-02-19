# Copyright 2014 OpenStack Foundation
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

from __future__ import absolute_import
import os
import kerberos

from keystone import auth
from keystone import config
from keystone import exception
from keystone import identity
from keystone.openstack.common import log as logging


CONF = config.CONF
METHOD_NAME = 'kerberos'
os.environ['KRB5_KTNAME'] = CONF.kerberos.keytab_file

LOG = logging.getLogger(__name__)


@dependency.requires('identity_api')
class Kerberos(auth.AuthMethodHandler):
    def __init__(self):
        servicename = CONF.kerberos.service_name
        self.service = 'HTTP@%s' % servicename
        try:
            principal = kerberos.getServerPrincipalDetails('HTTP', servicename)
        except kerberos.KrbError as ex:
            LOG.warn(_('Error while initializing kerberos library: %s'), ex)
        else:
            LOG.info(_('Service identified as Kerberos/%s'), principal)

    def kerberos_step(self, client_token):
        """
        Validates the client kerberos ticket within the system
        If it requires an extra validation it will send an extra
        authentication token. If the authentication suceeds it will
        return the user in the format (user@REALM) received.
        """
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
        except kerberos.GSSError as ex:
            LOG.error(_('Error during kerberos step: %s'), ex)
            pass
        finally:
            if state:
                kerberos.authGSSServerClean(state)
        return server_token, user

    def authenticate(self, context, auth_payload, user_context):
        """
        Authenticates the user if it presents a kerberos token
        If not it will resend the negotiate header. The client
        user is in the format (user@REALM) and it will be verified
        within the identity API.
        """
        auth_header = context['headers'].get('Authorization')
        if auth_header is None:
            raise exception.Unauthorized(method='Negotiate')

        client_token = ''.join(authHeader.split()[1:])
        server_token, user = self.kerberos_step(client_token)

        if user:
            names = user.rsplit('@', 1)
            username = names.pop(0)
            if names:
                domain_name = names[0]
                domain_ref = (self.identity_api.
                              get_domain_by_name(domain_name))
                domain_id = domain_ref['id']
            else:
                domain_id = CONF.identity.default_domain_id
            user_ref = self.identity_api.get_user_by_name(username,
                                                          domain_id)
            if 'user_id' not in user_context:
                user_context['user_id'] = user_ref['id']
        elif server_token:
            raise exception.Unauthorized(method='Negotiate',
                                         token=server_token)
        else:
            raise exception.Forbidden()
