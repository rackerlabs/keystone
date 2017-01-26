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


def filter_federated_objects(fed_ref):
    """Create a new reformatted federated dict using the one passed in.

    When returning federated objects with a user we only need the attributes
    idp_id, protocol_id, and unique_id. Therefore, we pull these elements out
    of the fed_ref and create a newly formatted dictionary with the needed
    information.

    :returns: new_fed_ref
    """
    if not fed_ref:
        return []

    fed = []
    idps = set()
    # Group idp protocols into their respective lists
    for fed_dict in fed_ref:
        if fed_dict['idp_id'] in idps:
            for idp_group in fed:
                if fed_dict['idp_id'] in idp_group['idp_id']:
                    idp_group['protocols'].append(
                        {
                            "protocol_id": fed_dict['protocol_id'],
                            "unique_id": fed_dict['unique_id']
                        }
                    )
        else:
            fed.append(
                {
                    "idp_id":fed_dict['idp_id'],
                    'protocols':[
                        {
                            "protocol_id": fed_dict['protocol_id'],
                            "unique_id": fed_dict['unique_id']
                        }
                    ]
                }
            )
            idps.add(fed_dict['idp_id'])
    return fed


@six.add_metaclass(abc.ABCMeta)
class ShadowUsersDriverBase(object):
    """Interface description for an Shadow Users driver."""

    @abc.abstractmethod
    def create_federated_user(self, federated_dict):
        """Create a new user with the federated identity.

        :param dict federated_dict: Reference to the federated user
        :param user_id: user ID for linking to the federated identity
        :returns dict: Containing the user reference

        """
        raise exception.NotImplemented()

    @abc.abstractmethod
    def get_federated_user(self, idp_id, protocol_id, unique_id):
        """Return the found user for the federated identity.

        :param idp_id: The identity provider ID
        :param protocol_id: The federation protocol ID
        :param unique_id: The unique ID for the user
        :returns dict: Containing the user reference

        """
        raise exception.NotImplemented()

    @abc.abstractmethod
    def update_federated_user_display_name(self, idp_id, protocol_id,
                                           unique_id, display_name):
        """Update federated user's display name if changed.

        :param idp_id: The identity provider ID
        :param protocol_id: The federation protocol ID
        :param unique_id: The unique ID for the user
        :param display_name: The user's display name

        """
        raise exception.NotImplemented()

    @abc.abstractmethod
    def get_user(self, user_id):
        """Return the found user.

        :param user_id: Unique identifier of the user
        :returns dict: Containing the user reference

        """
        raise exception.NotImplemented()

    @abc.abstractmethod
    def create_nonlocal_user(self, user_dict):
        """Create a new non-local user.

        :param dict user_dict: Reference to the non-local user
        :returns dict: Containing the user reference

        """
        raise exception.NotImplemented()

    @abc.abstractmethod
    def set_last_active_at(self, user_id):
        """Set the last active at date for the user.

        :param user_id: Unique identifier of the user

        """
        raise exception.NotImplemented()
