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

"""Keystone External Authentication Plugin"""

import abc

from keystone.common import config
from keystone import exception


CONF = config.CONF


class ExternalBase(object):
    _metaclass__ = abc.ABCMeta
    def authenticate(self, context, auth_info, auth_context):
        """Use REMOTE_USER to look up the user in the identity backend.

        auth_context is an in-out variable that will be updated with the
        user_id from the actual user pointed by the REMOTE_USER
        environment variable.
        """
        try:
            REMOTE_USER = context['REMOTE_USER']
        except KeyError:
            msg = _('No authenticated user')
            raise exception.Unauthorized(msg)
        try:
            user_ref = self._authenticate(REMOTE_USER, auth_info)
            auth_context['user_id'] = user_ref['id']
            if ('kerberos' in CONF.token.bind and
                    context.get('AUTH_TYPE', '').lower() == 'negotiate'):
                auth_context['bind']['kerberos'] = user_ref["name"]
        except Exception:
            msg = _('Unable to lookup user %s') % (REMOTE_USER)
            raise exception.Unauthorized(msg)

    @abc.abstractmethod
    def _authenticate(self, REMOTE_USER):
        """Look up the user in the identity backend.

        Return user_ref of raise exception.Unauthorized
        """
        pass


class ExternalDeprecatedGrizzly(ExternalBase):
    def _authenticate(self, REMOTE_USER, auth_info):
        """Use REMOTE_USER to look up the user in the identity backend

        Mimic thge bahaviour of external authentication and REMOTE_USER in
        the Grizzly release.
        """
        # FIXME(gyee): REMOTE_USER is not good enough since we are
        # requiring domain_id to do user lookup now. Try to get
        # the user_id from auth_info for now, assuming external auth
        # has check to make sure user is the same as the one specify
        # in "identity".
        if 'password' in auth_info.get_method_names():
            user_info = auth_info.get_method_data('password')
            user_ref = auth_info.lookup_user(user_info['user'])
            return user_ref
        else:
            msg = _('Unable to lookup user %s') % (REMOTE_USER)
            raise exception.Unauthorized(msg)


class ExternalDefault(ExternalBase):
    def _authenticate(self, REMOTE_USER, auth_info):
        """Use REMOTE_USER to look up the user in the identity backend."""
        domain_id = CONF.identity.default_domain_id
        user_ref = auth_info.identity_api.get_user_by_name(REMOTE_USER,
                                                           domain_id)
        return user_ref


class ExternalDomain(ExternalBase):
    def _authenticate(self, REMOTE_USER, auth_info):
        """Use REMOTE_USER to look up the user in the identity backend.

        If REMOTE_USER contains an `@` assume that the substring before the
        rightmost `@` is the username, and the substring after the @ is the
        domain name.
        """
        names = REMOTE_USER.rsplit('@', 1)
        username = names.pop(0)
        if names:
            domain_name = names[0]
            domain_ref = (auth_info.identity_api.
                            get_domain_by_name(domain_name))
            domain_id = domain_ref['id']
        else:
            domain_id = CONF.identity.default_domain_id
        user_ref = auth_info.identity_api.get_user_by_name(username,
                                                            domain_id)
        return user_ref
