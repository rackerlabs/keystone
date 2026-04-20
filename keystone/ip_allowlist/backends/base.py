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

"""Interface for the IP allowlist backend driver."""

import abc

from keystone import exception


class IPAllowlistDriverBase(metaclass=abc.ABCMeta):
    """Interface for managing per-user IP CIDR allowlists."""

    @abc.abstractmethod
    def list_allowed_cidrs(self, user_id):
        """Return all allowed CIDRs for a user.

        :param user_id: The user ID.
        :returns: A list of dicts with keys ``id``, ``user_id``, ``cidr``,
                  ``description``, ``created_at``.
        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def get_allowed_cidr(self, user_id, entry_id):
        """Return a single allowlist entry.

        :param user_id: The user ID.
        :param entry_id: The entry ID.
        :returns: A dict.
        :raises keystone.exception.IPAllowlistEntryNotFound: If not found.
        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def create_allowed_cidr(self, user_id, entry_id, entry):
        """Create a new CIDR allowlist entry for a user.

        :param user_id: The user ID.
        :param entry_id: The unique ID for the new entry.
        :param entry: A dict with ``cidr`` and optionally ``description``.
        :returns: The created entry dict.
        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def delete_allowed_cidr(self, user_id, entry_id):
        """Delete a CIDR allowlist entry.

        :param user_id: The user ID.
        :param entry_id: The entry ID.
        :raises keystone.exception.IPAllowlistEntryNotFound: If not found.
        """
        raise exception.NotImplemented()  # pragma: no cover
