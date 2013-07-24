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


from keystone.common import dependency
from keystone.common import extension
from keystone.common import logging
from keystone.common import manager
from keystone import config
from keystone import exception


CONF = config.CONF
LOG = logging.getLogger(__name__)

extension_data = {
    'name': 'Openstack Keystone Endpoint Filter API',
    'namespace': 'http://docs.openstack.org/identity/api/ext/'
                 'OS-EP-FILTER/v1.0',
    'alias': 'OS-EP-FILTER',
    'updated': '2013-07-23T12:00:0-00:00',
    'description': 'Openstack Keystone Endpoint Filter API.',
    'links': [
        {
            'rel': 'describedby',
            # TODO(ayoung): needs a description
            'type': 'text/html',
            'href': 'https://github.com/openstack/identity-api',
        }
    ]}
extension.register_admin_extension(extension_data['alias'], extension_data)


@dependency.provider('ep_filter_api')
class Manager(manager.Manager):
    """Default pivot point for the Endpoint Filter backend.

    See :mod:`keystone.common.manager.Manager` for more details on how this
    dynamically calls the backend.

    """

    def __init__(self):
        super(Manager, self).__init__(CONF.os_ep_filter.driver)


class Driver(object):
    """Interface description for a Endpoint Filter driver."""

    def create_ep_filter_association(self, endpoint_id, project_id):
        """Creates an endpoint to project association.

        :raises: keystone.exception.ProjectNotFound,
                 keystone.exception.EndpointNotFound

        """
        raise exception.NotImplemented()

    def remove_ep_filter_association(self, endpoint_id, project_id):
        """Removes an endpoint to project association.

        :raises: exception.NotFound

        """
        raise exception.NotImplemented()

    def check_endpoint_in_project(self, endpoint_id, project_id):
        """Checks if an endpoint is assiciated with a project.

        :raises: keystone.exception.ProjectNotFound,
                 keystone.exception.EndpointNotFound,
                 exception.NotFound

        """
        raise exception.NotImplemented()

    def list_endpoints_in_project(self, project_id):
        """List all endpoints associated with a project.

        :raises: keystone.exception.ProjectNotFound
        :returns: a list of endpoint ids or an empty list.

        """
        raise exception.NotImplemented()

    def list_project_endpoints(self, endpoint_id):
        """List all endpoints associated with a project.

        :raises: keystone.exception.EndpointNotFound
        :returns: a list of projects or an empty list.

        """
        raise exception.NotImplemented()
