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

import abc

import six

from keystone.common import dependency
from keystone.common import extension
from keystone.common import manager
from keystone import config
from keystone import exception
from keystone.openstack.common import log


CONF = config.CONF
LOG = log.getLogger(__name__)

extension_data = {
    'name': 'OpenStack Keystone Grouping API',
    'namespace': 'http://docs.openstack.org/identity/api/ext/'
                 'OS-EP-GROUPING/v1.0',
    'alias': 'OS-EP-GROUPING',
    'updated': '2013-07-23T12:00:0-00:00',
    'description': 'OpenStack Keystone Endpoint Grouping API.',
    'links': [
        {
            'rel': 'describedby',
            # TODO(ayoung): needs a description
            'type': 'text/html',
            'href': 'https://github.com/openstack/identity-api/blob/master'
                    '/openstack-identity-api/v3/src/markdown/'
                    'identity-api-v3-os-ep-grouping-ext.md',
        }
    ]}
extension.register_admin_extension(extension_data['alias'], extension_data)


@dependency.provider('endpoint_grouping_api')
class Manager(manager.Manager):
    """Default pivot point for the Endpoint Grouping backend.

    See :mod:`keystone.common.manager.Manager` for more details on how this
    dynamically calls the backend.

    """

    def __init__(self):
        super(Manager, self).__init__(CONF.endpoint_grouping.driver)


@six.add_metaclass(abc.ABCMeta)
class Driver(object):
    """Interface description for an Endpoint Grouping driver."""

    @abc.abstractmethod
    def create_endpoint_group(self, endpoint_group_id, endpoint_group):
        """Creates an endpoint to project association.

        :param endpoint_group_id: identity of endpoint to associate
        :type endpoint_group_id: string
        :param endpoint_group: group data
        :type endpoint_group: json
        :raises: keystone.exception.Conflict,
        :returns: None.

        """
        raise exception.NotImplemented()

    @abc.abstractmethod
    def get_endpoint_group(self, endpoint_group_id):
        """Get an endpoint to project association.

        :param endpoint_group_id: identity of endpoint to associate
        :type endpoint_group_id: string
        :param endpoint_group: group data
        :type endpoint_group: json
        :raises: keystone.exception.Conflict,
        :returns: None.

        """
        raise exception.NotImplemented()

    @abc.abstractmethod
    def remove_endpoint_group(self, endpoint_group_id):
        """Removes an endpoint to project association.

        :param endpoint_group_id: identity of endpoint to associate
        :type endpoint_group_id: string
        :raises: keystone.exception.Conflict,
        :returns: None.

        """
        raise exception.NotImplemented()

    @abc.abstractmethod
    def add_endpoint_group_to_project(self, project_id, endpoint_group_id):
        """Adds an endpoint to project association.

        :param endpoint_group_id: identity of endpoint to associate
        :type endpoint_group_id: string
        :param endpoint_group: group data
        :type endpoint_group: json
        :raises: keystone.exception.Conflict,
        :returns: None.

        """
        raise exception.NotImplemented()

    @abc.abstractmethod
    def check_endpoint_group_in_project(self, project_id, endpoint_group_id):
        """Checks if an endpoint to project association exists.

        :param endpoint_group_id: identity of endpoint to associate
        :type endpoint_group_id: string
        :param endpoint_group: group data
        :type endpoint_group: json
        :raises: keystone.exception.Conflict,
        :returns: None.

        """
        raise exception.NotImplemented()

    @abc.abstractmethod
    def list_endpoint_groups_for_project(self, project_id):
        """Lists all the endpoint to project associations for a given project id.

        :param endpoint_group_id: identity of endpoint to associate
        :type endpoint_group_id: string
        :param endpoint_group: group data
        :type endpoint_group: json
        :raises: keystone.exception.Conflict,
        :returns: None.

        """
        raise exception.NotImplemented()

    @abc.abstractmethod
    def remove_endpoint_group_from_project(self, project_id, endpoint_group_id):
        """Removes an endpoint to project association.

        :param endpoint_group_id: identity of endpoint to associate
        :type endpoint_group_id: string
        :param endpoint_group: group data
        :type endpoint_group: json
        :raises: keystone.exception.Conflict,
        :returns: None.

        """
        raise exception.NotImplemented()        

    @abc.abstractmethod
    def grant_endpoint_group_in_project_to_user(self, project_id, endpoint_group_id, user_id):
        """Creates an endpoint to project association.

        :param endpoint_group_id: identity of endpoint to associate
        :type endpoint_group_id: string
        :param endpoint_group: group data
        :type endpoint_group: json
        :raises: keystone.exception.Conflict,
        :returns: None.

        """
        raise exception.NotImplemented()

    @abc.abstractmethod
    def check_endpoint_group_in_project_to_user(self, project_id, endpoint_group_id, user_id):
        """Checks an endpoint to project association.

        :param endpoint_group_id: identity of endpoint to associate
        :type endpoint_group_id: string
        :param endpoint_group: group data
        :type endpoint_group: json
        :raises: keystone.exception.Conflict,
        :returns: None.

        """
        raise exception.NotImplemented()

    @abc.abstractmethod
    def list_endpoint_groups_in_project_granted_to_user(self, project_id, user_id):
        """Creates an endpoint to project association.

        :param endpoint_group_id: identity of endpoint to associate
        :type endpoint_group_id: string
        :param endpoint_group: group data
        :type endpoint_group: json
        :raises: keystone.exception.Conflict,
        :returns: None.

        """
        raise exception.NotImplemented()

    @abc.abstractmethod
    def remove_endpoint_group_in_project_to_user(self, project_id, endpoint_group_id, user_id):
        """Creates an endpoint to project association.

        :param endpoint_group_id: identity of endpoint to associate
        :type endpoint_group_id: string
        :param endpoint_group: group data
        :type endpoint_group: json
        :raises: keystone.exception.Conflict,
        :returns: None.

        """
        raise exception.NotImplemented()

    @abc.abstractmethod
    def list_endpoint_groups(self):
        """Creates an endpoint to project association.

        :raises: keystone.exception.Conflict,
        :returns: None.

        """
        raise exception.NotImplemented()

    @abc.abstractmethod
    def list_projects_for_endpoint_group(self, endpoint_group_id):
        """Creates an endpoint to project association.

        :param endpoint_group_id: identity of endpoint to associate
        :type endpoint_group_id: string
        :raises: keystone.exception.Conflict,
        :returns: None.

        """
        raise exception.NotImplemented()

    @abc.abstractmethod
    def get_filter_for_endpoint_group(self, endpoint_group_id):
        """Creates an endpoint to project association.

        :param endpoint_group_id: identity of endpoint to associate
        :type endpoint_group_id: string
        :raises: keystone.exception.Conflict,
        :returns: None.

        """
        raise exception.NotImplemented()