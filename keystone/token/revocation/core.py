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

"""Main entry point into the Token Revocation Service."""

from keystone.common import dependency
from keystone.common import logging
from keystone.common import manager
from keystone import config
from keystone import exception

CONF = config.CONF
LOG = logging.getLogger(__name__)


@dependency.provider('revoked_token_api')
class Manager(manager.Manager):
    """Default pivot point for the Revoked Token backend.

    See :mod:`keystone.common.manager.Manager` for more details on how this
    dynamically calls the backend.

    """

    def __init__(self):
        super(Manager, self).__init__(CONF.token.revocation_driver)


class Driver(object):
    def list_revoked_tokens(self):
        """Returns a list of all revoked tokens

        :returns: list of token_id's
        """
        raise exception.NotImplemented()

    def add_revoked_token(self, token_ref):
        """Adds a token to the revoked token list.

        :param token_ref: token data
        :type token_ref: dict
        :return: None.
        :raises: keystone.exception.TokenNotFound
        """
        raise exception.NotImplemented()

    def add_revoked_tokens(self, revoke_tokens_list, flush_all=False):
        """
        Adds each token in the token_ref_list to the revocation list.

        :param revoke_tokens_list: list of token_refs
        :type revoke_tokens_list: list
        :return: None
        """
        raise exception.NotImplemented()

    def flush_expired_tokens(self):
        """Remove expired tokens from the revocation list."""
        raise exception.NotImplemented()
