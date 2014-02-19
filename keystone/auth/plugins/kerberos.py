# vim: tabstop=4 shiftwidth=4 softtabstop=4

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
import kerberos as krb_lib
import os

from keystone import auth
from keystone import config
from keystone import exception
from keystone import identity
from keystone.openstack.common import log as logging


CONF = config.CONF
METHOD_NAME = 'kerberos'

LOG = logging.getLogger(__name__)


class Kerberos(auth.AuthMethodHandler):
    def __init__(self):
        self.identity_api = identity.Manager()
        servicename = CONF.kerberos.service_name
        self.service = 'HTTP@%s' % servicename
        os.environ['KRB5_KTNAME'] = CONF.kerberos.keytab_file
        try:
            principal = krb_lib.getServerPrincipalDetails('HTTP', servicename)
        except krb_lib.KrbError as ex:
            LOG.warn(_('Error while initializing kerberos library: %s'), ex)
        else:
            LOG.info(_('Kerberos is identifying as %s'), principal)

    def kerberos_step(self, client_token):
        state = None
        server_token = None
        user = None
        try:
            rc, state = krb_lib.authGSSServerInit(self.service)
            if rc == krb_lib.AUTH_GSS_COMPLETE:
                rc = krb_lib.authGSSServerStep(state, client_token)
                if rc == krb_lib.AUTH_GSS_COMPLETE:
                    server_token = krb_lib.authGSSServerResponse(state)
                    user = krb_lib.authGSSServerUserName(state)
                elif rc == krb_lib.AUTH_GSS_CONTINUE:
                    server_token = krb_lib.authGSSServerResponse(state)
        except krb_lib.GSSError as ex:
            LOG.error(_('Error during kerberos step: %s'), ex)
            pass
        finally:
            if state:
                krb_lib.authGSSServerClean(state)
        return server_token, user

    def authenticate(self, context, auth_payload, user_context):
        authHeader = context['headers'].get('Authorization')
        if authHeader is None:
            raise exception.UnauthorizedNegotiate()

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
            raise exception.UnauthorizedNegotiate(server_token)
        else:
            raise exception.Forbidden()
