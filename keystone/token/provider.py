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

"""Token lifecycle management interface."""


from keystone.common import dependency
from keystone.common import logging
from keystone.common import manager
from keystone import config
from keystone import exception


CONF = config.CONF
LOG = logging.getLogger(__name__)


# supported token versions
V2 = 'v2.0'
V3 = 'v3.0'


class UnsupportedTokenVersionException(Exception):
    """Token version is unrecognizable or unsupported."""
    pass


@dependency.provider('token_provider_api')
class Manager(manager.Manager):
    """Default pivot point for the token provider backend.

    See :mod:`keystone.common.manager.Manager` for more details on how this
    dynamically calls the backend.

    """

    def __init__(self):
        super(Manager, self).__init__(CONF.token.provider)


class Driver(object):
    """Interface description for a Token provider."""

    def get_token_version(self, token_data):
        """Return the version of the given token data.

        If the given token data is unrecognizable,
        UnsupportedTokenVersionException is raised.

        """
        raise exception.NotImplemented()

    def issue_token(self, user_id, method_names, version='v3.0',
                    expires_at=None,
                    project_id=None, domain_id=None,
                    auth_context=None, **kwargs):
        """Issue a V3 token.

        :param user_id: identity of the user
        :type user_id: string
        :param method_names: authentication method names
        :type methods: list of strings
        :param version: version of the token to be issued
        :type version: string
        :param expires_at: token expiration
        :type: date
        :param project_id: identity of the scoped project
        :type project_id: string
        :param domain_id: identity of the scoped domain
        :type domain_id: string
        :param auth_context: authentication context
        :type auth_context: dict
        :param kwargs: other information to assist token creation
        :type kwargs: free from keyword arguments
        :returns: (token_id, token_data)
        :raises: keystone.exception.TokenNotFound

        """
        raise exception.NotImplemented()

    def revoke_token(self, token_id):
        """Revoke a given token.

        :param token_id: identity of the token
        :type token_id: string
        :returns: None.
        :raises: keystone.exception.TokenNotFound
        """
        raise exception.NotImplemented()

    def validate_token(self, token_id, belongs_to=None, version='v3.0',
                       **kwargs):
        """Validate the given token and return the token data.

        Must raise Unauthorized exception if unable to validate token.

        :param token_id: identity of the token
        :type token_id: string
        :param belongs_to: identity of the scoped project to validate
        :type belongs_to: string
        :param version: version of the token to be validated
        :type version: string
        :param kwargs: other information to assist token validation
        :type kwargs: free from keyword arguments
        :returns: token data
        :raises: keystone.exception.Unauthorized

        """
        raise exception.NotImplemented()

    def check_token(self, token_id, belongs_to=None, **kwargs):
        """Check the validity of the given V3 token.

        Must raise Unauthorized exception if  unable to check token.

        :param token_id: identity of the token
        :type token_id: string
        :param belongs_to: identity of the scoped project to validate
        :type belongs_to: string
        :param kwargs: other information to assist token validation
        :type kwargs: free from keyword arguments
        :returns: None
        :raises: keystone.exception.Unauthorized

        """
