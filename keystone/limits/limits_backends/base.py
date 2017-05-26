# Copyright 2017 SUSE Linux Gmbh
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

from oslo_log import log
import six

from keystone import exception


LOG = log.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class LimitDriverBase(object):

    @abc.abstractmethod
    def create_limit(self, limit_id, limit):
        """Create a new limit.

        :raises keystone.exception.Conflict: If a duplicate limit exists.

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def list_limits(self):
        """List all limits.

        :returns: a list of limit_refs or an empty list.

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def get_limit(self, project_id, service_type, region, resource_name):
        """Get a limit.

        :returns: limit_ref
        :raises keystone.exception.LimitNotFound: If limit doesn't
            exist.

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def update_limit(self, project_id, service_type, region, resource_name,
                     limit):
        """Update an existing limit.

        :raises keystone.exception.LimitNotFound: If limit doesn't
            exist.
        :raises keystone.exception.Conflict: If a duplicate limit exists.

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def delete_limit(self, project_id, service_type, region, resource_name):
        """Delete an existing limit.

        :raises keystone.exception.LimitNotFound: If limit doesn't
            exist.

        """
        raise exception.NotImplemented()  # pragma: no cover
