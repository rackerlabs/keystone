# Copyright 2012 OpenStack Foundation
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

import abc

import six

from keystone import exception


@six.add_metaclass(abc.ABCMeta)
class Provider(object):
    """Interface description for a Token provider."""

    @abc.abstractmethod
    def get_token_version(self, token_data):
        """Return the version of the given token data.

        If the given token data is unrecognizable,
        UnsupportedTokenVersionException is raised.

        :param token_data: token_data
        :type token_data: dict
        :returns: token version string
        :raises keystone.exception.UnsupportedTokenVersionException:
            If the token version is not expected.
        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def validate_token(self, token_ref):
        """Validate the given V3 token and return the token_data.

        :param token_ref: the token reference
        :type token_ref: dict
        :returns: token data
        :raises keystone.exception.TokenNotFound: If the token doesn't exist.
        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def generate_id_and_issued_at(self, token):
        """Generate a token based on the information provided.

        :param token: A token object containing information about the
                      authorization context of the request.
        :type token: `keystone.models.token.TokenModel`
        :returns: tuple containing an ID for the token and the issued at time
                  of the token (token_id, issued_at).
        """
        raise exception.NotImplemented()  # pragma: no cover
