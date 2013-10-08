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

import six

from keystone import auth
from keystone.common import config
from keystone.common import utils
from keystone import exception
from keystone.openstack.common import log as logging


LOG = logging.getLogger(__name__)

CONF = config.CONF


@six.add_metaclass(abc.ABCMeta)
class Base(auth.AuthMethodHandler):
    def authenticate(self, context, auth_info, auth_context):
        """Use REMOTE_USER to look up the user in the identity backend.

        auth_context is an in-out variable that will be updated with the
        user_id from the actual user from the REMOTE_USER env variable.
        """
        try:
            REMOTE_USER = context['environment']['REMOTE_USER']
        except KeyError:
            msg = _('No authenticated user')
            raise exception.Unauthorized(msg)
        try:
            user_ref = self._authenticate(REMOTE_USER, context, auth_info)
            auth_context['user_id'] = user_ref['id']
            if ('kerberos' in CONF.token.bind and
                (context['environment'].get('AUTH_TYPE', '').lower()
                 == 'negotiate')):
                auth_context['bind']['kerberos'] = user_ref['name']
        except Exception:
            msg = _('Unable to lookup user %s') % (REMOTE_USER)
            raise exception.Unauthorized(msg)

    @abc.abstractmethod
    def _authenticate(self, remote_user, context, auth_info):
        """Look up the user in the identity backend.

        Return user_ref
        """
        pass


class DeprecatedGrizzly(Base):
    @utils.deprecated(as_of=utils.deprecated.ICEHOUSE,
                      in_favor_of='keystone.auth.external.Default',
                      remove_in=+1)
    def __init__(self):
        super(DeprecatedGrizzly, self).__init__()

    def _authenticate(self, remote_user, auth_info):
        """Use remote_user to look up the user in the identity backend

        Mimic the behaviour of external authentication and remote_user in
        the Grizzly release.
        """
        # FIXME(aloga): remote_user is not good enough since we are
        # requiring domain_id to do user lookup now. Try to get
        # the user_id from auth_info for now, assuming external auth
        # has checked to make sure the user is the same as the one specified
        # in "identity".
        if 'password' in auth_info.get_method_names():
            user_info = auth_info.get_method_data('password')
            user_ref = auth_info.lookup_user(user_info['user'])
            if remote_user != user_ref['name']:
                msg = _('remote_user does not match supplied credentials '
                        '%(remote)s != %(name)s') % {"remote": remote_user,
                                                     "name": user_ref['name']}
                LOG.warning(msg)
                msg = _('Unable to lookup user %s') % (remote_user)
                raise Exception(msg)
            return user_ref
        else:
            msg = _("The 'password' method must be defined in methods "
                    "for external.DeprecatedGrizzly")
            raise Exception(msg)


class Default(Base):
    def _authenticate(self, remote_user, context, auth_info):
        """Use remote_user to look up the user in the identity backend."""
        domain_id = CONF.identity.default_domain_id
        user_ref = auth_info.identity_api.get_user_by_name(remote_user,
                                                           domain_id)
        return user_ref


class Domain(Base):
    def _authenticate(self, remote_user, context, auth_info):
        """Use remote_user to look up the user in the identity backend.

        The domain will be extracted from the REMOTE_DOMAIN environment
        variable if present. If not, the default domain will be used.
        """

        username = remote_user
        try:
            domain_name = context['environment']['REMOTE_DOMAIN']
        except KeyError:
            domain_id = CONF.identity.default_domain_id
        else:
            domain_ref = (auth_info.identity_api.
                          get_domain_by_name(domain_name))
            domain_id = domain_ref['id']

        user_ref = auth_info.identity_api.get_user_by_name(username,
                                                           domain_id)
        return user_ref


class ExternalDefault(Default):
    """Deprecated. Please use keystone.auth.external.Default instead."""

    @utils.deprecated(as_of=utils.deprecated.ICEHOUSE,
                      in_favor_of='keystone.auth.external.Default',
                      remove_in=+1)
    def __init__(self):
        super(ExternalDefault, self).__init__()


class ExternalDomain(Domain):
    """Deprecated. Please use keystone.auth.external.Domain instead."""

    @utils.deprecated(as_of=utils.deprecated.ICEHOUSE,
                      in_favor_of='keystone.auth.external.Domain',
                      remove_in=+1)
    def __init__(self):
        super(ExternalDomain, self).__init__()
