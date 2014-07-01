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

"""Keystone External Authentication Plugins"""

import abc

import six

from keystone import auth
from keystone.common import config
from keystone.common import dependency
from keystone import exception
from keystone.openstack.common.gettextutils import _
from keystone.openstack.common import log
from keystone.openstack.common import versionutils


CONF = config.CONF

LOG = log.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class Base(auth.AuthMethodHandler):

    method = 'external'

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
            user_ref = self._authenticate(REMOTE_USER, context)
            auth_context['user_id'] = user_ref['id']
            if ('kerberos' in CONF.token.bind and
                (context['environment'].get('AUTH_TYPE', '').lower()
                 == 'negotiate')):
                auth_context['bind']['kerberos'] = user_ref['name']
        except Exception:
            msg = _('Unable to lookup user %s') % (REMOTE_USER)
            raise exception.Unauthorized(msg)

    @abc.abstractmethod
    def _authenticate(self, remote_user, context):
        """Look up the user in the identity backend.

        Return user_ref
        """
        pass


@dependency.requires('identity_api')
class DefaultDomain(Base):
    def _authenticate(self, remote_user, context):
        """Use remote_user to look up the user in the identity backend."""
        domain_id = CONF.identity.default_domain_id
        user_ref = self.identity_api.get_user_by_name(remote_user, domain_id)
        return user_ref


@dependency.requires('assignment_api', 'identity_api')
class Domain(Base):
    def _authenticate(self, remote_user, context):
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
            domain_ref = self.assignment_api.get_domain_by_name(domain_name)
            domain_id = domain_ref['id']

        user_ref = self.identity_api.get_user_by_name(username, domain_id)
        return user_ref


@dependency.requires('assignment_api', 'identity_api')
class KerberosDomain(Domain):
    """Allows `kerberos` as a method."""
    method = 'kerberos'

    def _authenticate(self, remote_user, context):
        auth_type = context['environment'].get('AUTH_TYPE')
        if auth_type != 'Negotiate':
            raise exception.Unauthorized(_("auth_type is not Negotiate"))
        return super(KerberosDomain, self)._authenticate(remote_user, context)


class ExternalDefault(DefaultDomain):
    """Deprecated. Please use keystone.auth.external.DefaultDomain instead."""

    @versionutils.deprecated(
        as_of=versionutils.deprecated.ICEHOUSE,
        in_favor_of='keystone.auth.external.DefaultDomain',
        remove_in=+1)
    def __init__(self):
        super(ExternalDefault, self).__init__()


class ExternalDomain(Domain):
    """Deprecated. Please use keystone.auth.external.Domain instead."""

    @versionutils.deprecated(
        as_of=versionutils.deprecated.ICEHOUSE,
        in_favor_of='keystone.auth.external.Domain',
        remove_in=+1)
    def __init__(self):
        super(ExternalDomain, self).__init__()


@dependency.requires('identity_api')
class LegacyDefaultDomain(Base):
    """Deprecated. Please use keystone.auth.external.DefaultDomain instead.

    This plugin exists to provide compatibility for the unintended behavior
    described here: https://bugs.launchpad.net/keystone/+bug/1253484

    """

    @versionutils.deprecated(
        as_of=versionutils.deprecated.ICEHOUSE,
        in_favor_of='keystone.auth.external.DefaultDomain',
        remove_in=+1)
    def __init__(self):
        super(LegacyDefaultDomain, self).__init__()

    def _authenticate(self, remote_user, context):
        """Use remote_user to look up the user in the identity backend."""
        # NOTE(dolph): this unintentionally discards half the REMOTE_USER value
        names = remote_user.split('@')
        username = names.pop(0)
        domain_id = CONF.identity.default_domain_id
        user_ref = self.identity_api.get_user_by_name(username, domain_id)
        return user_ref


@dependency.requires('assignment_api', 'identity_api')
class LegacyDomain(Base):
    """Deprecated. Please use keystone.auth.external.Domain instead."""

    @versionutils.deprecated(
        as_of=versionutils.deprecated.ICEHOUSE,
        in_favor_of='keystone.auth.external.Domain',
        remove_in=+1)
    def __init__(self):
        super(LegacyDomain, self).__init__()

    def _authenticate(self, remote_user, context):
        """Use remote_user to look up the user in the identity backend.

        If remote_user contains an `@` assume that the substring before the
        rightmost `@` is the username, and the substring after the @ is the
        domain name.
        """
        names = remote_user.rsplit('@', 1)
        username = names.pop(0)
        if names:
            domain_name = names[0]
            domain_ref = self.assignment_api.get_domain_by_name(domain_name)
            domain_id = domain_ref['id']
        else:
            domain_id = CONF.identity.default_domain_id
        user_ref = self.identity_api.get_user_by_name(username, domain_id)
        return user_ref


@dependency.requires('identity_api')
class X509SSLCert(auth.AuthMethodHandler):
    """X.509 SSL client certificate authentication.

    This plugin is not domain-aware.

    This method must be used in conjunction with Apache mod_ssl. This also
    implies that Keystone must also be running in Apache mod_wsgi.

    In order for Apache mod_ssl to convey the SSL client certifciate
    information in the request environment, the `SSLOptions` directive must
    contains `+StdEnvVars` and the `SSLUserName` directive must set to a
    valid SSL requirement enviroment attribute.
    For example::

        SSLOptions +StdEnvVars
        SSLUserName SSL_CLIENT_S_DN_CN

    .. note::

        SSLUserName directive must not be used with +FakeBasicAuth option.

    For more details, please refer to
    `Apache mod_ssl  <http://httpd.apache.org/docs/2.2/mod/mod_ssl.html>`_

    The auth method accepts the following configurations from the
    `[x509_ssl_cert_auth]` section in the Keystone configuration file.

    - `user_id_attribute` - the SSL client certificate attribute where
                            Keystone user_id is conveyed.
    - `username_attribute` - the SSL client certificate attribute where
                             Keystone username is conveyed.
    - `user_domain_id_attribute` - the SSL client certificate attribute
                                   where Keystone user domain ID is conveyed
                                   Will be ignored if plugin is not
                                   domain-aware.
    - `user_domain_name_attribute` - the SSL client certificate attribute
                                     where Keystone user domain name is
                                     conveyed. Will be ignored if plugin is
                                     not domain-aware.

    The Keystone identity must be established from the above attributes.

    """
    method = 'x509'

    def _get_attribute(self, context, attribute_name):
        if attribute_name is not None:
            return context['environment'].get(attribute_name)

    def _get_domain_attributes(self, context):
        # use default domain ID as this plugin is not domain-aware
        return (CONF.identity.default_domain_id, None)

    def authenticate(self, context, auth_info, auth_context):
        user_id = self._get_attribute(
            context,
            CONF.x509_ssl_cert_auth.user_id_attribute)
        username = self._get_attribute(
            context,
            CONF.x509_ssl_cert_auth.username_attribute)

        (user_domain_id, user_domain_name) = self._get_domain_attributes(
            context)

        try:
            if user_id:
                user_ref = self.identity_api.get_user(user_id)
            elif username and (user_domain_id or user_domain_name):
                if user_domain_name and not user_domain_id:
                    user_domain_id = self.identity_api.get_domain_by_name(
                        user_domain_name)['id']
                user_ref = self.identity_api.get_user_by_name(username,
                                                              user_domain_id)
            auth_context['user_id'] = user_ref['id']
        except (exception.UserNotFound, exception.DomainNotFound) as e:
            LOG.exception(e)
            raise exception.Unauthorized(e)


class X509SSLCertDomain(X509SSLCert):
    """Domain-aware X.509 SSL client certificate authentication."""

    def _get_domain_attributes(self, context):
        user_domain_id = self._get_attribute(
            context,
            CONF.x509_ssl_cert_auth.user_domain_id_attribute)
        user_domain_name = self._get_context(
            context,
            CONF.x509_ssl_cert_auth.user_domain_name_attribute)

        return (user_domain_id, user_domain_name)
