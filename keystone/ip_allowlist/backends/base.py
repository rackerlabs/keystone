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
    """Interface for managing IP CIDR allowlists per target.

    A target is the tuple ``(target_type, target_id)`` where ``target_type``
    is one of ``'user'``, ``'domain'`` or ``'project'``.
    """

    @abc.abstractmethod
    def list_allowed_cidrs(self, target_type, target_id):
        """Return all allowed CIDRs for a target.

        :param target_type: One of ``'user'``, ``'domain'``, ``'project'``.
        :param target_id: The target ID.
        :returns: A list of dicts with keys ``id``, ``target_type``,
                  ``target_id``, ``cidr``, ``description``, ``created_at``.
        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def get_allowed_cidr(self, target_type, target_id, entry_id):
        """Return a single allowlist entry.

        :raises keystone.exception.IPAllowlistEntryNotFound: If not found.
        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def create_allowed_cidr(self, target_type, target_id, entry_id, entry):
        """Create a new CIDR allowlist entry for a target.

        :param entry: A dict with ``cidr`` and optionally ``description``.
        :returns: The created entry dict.
        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def delete_allowed_cidr(self, target_type, target_id, entry_id):
        """Delete a CIDR allowlist entry.

        :raises keystone.exception.IPAllowlistEntryNotFound: If not found.
        """
        raise exception.NotImplemented()  # pragma: no cover
