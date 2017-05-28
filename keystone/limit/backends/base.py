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
class RegisteredLimitDriverBase(object):

    @abc.abstractmethod
    def create_registered_limit(self, limit):
        """Create a new registered limit.

        :raises keystone.exception.Conflict: If a duplicate limit exists.

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def list_registered_limits(self, hints):
        """List all registered limits.

        :param hints: contains the list of filters yet to be satisfied.
                      Any filters satisfied here will be removed so that
                      the caller will know if any filters remain.

        :returns: a list of limit_refs or an empty list.

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def get_registered_limit(self, service_type, region, resource_name):
        """Get a registered limit.

        :returns: limit_ref
        :raises keystone.exception.RegisteredLimitNotFound: If limit doesn't
            exist.

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def update_registered_limit(self, limit):
        """Update an existing registered limit.

        :raises keystone.exception.RegisteredLimitNotFound: If limit doesn't
            exist.
        :raises keystone.exception.Conflict: If a duplicate limit exists.

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def delete_registered_limit(self, service_type, region, resource_name):
        """Delete an existing registered limit.

        :raises keystone.exception.RegisteredLimitNotFound: If
            registered_limit doesn't exist.

        """
        raise exception.NotImplemented()  # pragma: no cover


@six.add_metaclass(abc.ABCMeta)
class LimitDriverBase(object):

    @abc.abstractmethod
    def create_limit(self, limit_id, limit):
        """Create a new limit.

        :raises keystone.exception.Conflict: If a duplicate limit exists.

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def list_limits(self, project_id, hints):
        """List all limits for project_id.

        :param hints: contains the list of filters yet to be satisfied.
                      Any filters satisfied here will be removed so that
                      the caller will know if any filters remain.

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
