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


from keystone.common import config as keystone_config
from keystone.common import controller
from keystone.common import dependency
from keystone.common import extension
from keystone.common import logging
from keystone.common import manager
from keystone.common import wsgi
from keystone import config
from keystone import exception


keystone_config.register_str(
    'driver', group='os_ep_filter',
    default='keystone.contrib.endpoint_filter.backends.sql.EndpointFilter')

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


class EndpointFilterExtension(wsgi.ExtensionRouter):
    def add_routes(self, mapper):
        ep_filter_controller = EndpointFilterV3Controller()
        mapper.connect('/OS-EP-FILTER/endpoints/{endpoint_id}/projects',
                       controller=ep_filter_controller,
                       action='list_associated_projects',
                       conditions=dict(method=['GET']))
        mapper.connect('/OS-EP-FILTER/projects/{project_id}'
                       '/endpoints/{endpoint_id}',
                       controller=ep_filter_controller,
                       action='create_ep_filter_association',
                       conditions=dict(method=['PUT']))
        mapper.connect('/OS-EP-FILTER/projects/{project_id}'
                       '/endpoints/{endpoint_id}',
                       controller=ep_filter_controller,
                       action='check_ep_filter_association',
                       conditions=dict(method=['HEAD']))
        mapper.connect('/OS-EP-FILTER/projects/{project_id}/endpoints',
                       controller=ep_filter_controller,
                       action='get_ep_filter_associations',
                       conditions=dict(method=['GET']))
        mapper.connect('/OS-EP-FILTER/projects/{project_id}'
                       '/endpoints/{endpoint_id}',
                       controller=ep_filter_controller,
                       action='remove_ep_filter_association',
                       conditions=dict(method=['DELETE']))


@dependency.requires('catalog_api', 'identity_api')
class EndpointFilterV3Controller(controller.V3Controller):

    def __init__(self):
        self.ep_filter_api = Manager()
        super(EndpointFilterV3Controller, self).__init__()

    @controller.protected
    def create_ep_filter_association(self, context, project_id, endpoint_id):
        """Establishes an association between an endpoint and a project."""
        endpoint = self.catalog_api.get_endpoint(endpoint_id)
        if endpoint is None:
            raise exception.EndpointNotFound

        project = self.identity_api.get_project(project_id)
        if project is None:
            raise exception.ProjectNotFound

        try:
            return self.ep_filter_api.create_ep_filter_association(endpoint_id,
                                                                   project_id)
        except exception as error:
            raise error

    @controller.protected
    def check_ep_filter_association(self, context, project_id, endpoint_id):
        """Verifies endpoint is currently associated with given project."""
        try:
            endpoint = self.catalog_api.get_endpoint(endpoint_id)
            if endpoint is None:
                raise exception.EndpointNotFound

            return self.ep_filter_api.check_endpoint_in_project(endpoint_id,
                                                                project_id)
        except exception.ProjectNotFound as pnf:
            raise pnf

    @controller.protected
    def get_ep_filter_associations(self, context, project_id):
        """Lists all the endpoints currently associated with a give project."""
        refs = self.ep_filter_api.list_endpoints_in_project(project_id)
        from keystone.catalog import controllers as catalog_controllers
        #api = self.catalog_api
        endpoints = [self.catalog_api.get_endpoint(
            x.endpoint_id) for x in refs]
        return catalog_controllers.EndpointV3.wrap_collection(context,
                                                              endpoints)

    @controller.protected
    def remove_ep_filter_association(self, context, project_id, endpoint_id):
        """Remove the endpoint fro the association wuth given project."""
        return self.ep_filter_api.remove_ep_filter_association(endpoint_id,
                                                               project_id)

    @controller.protected
    def list_associated_projects(self, context, endpoint_id):
        """Return a list of projects associated with the endpoint."""
        refs = self.ep_filter_api.list_project_endpoints(endpoint_id)
        if refs is None:
            raise exception.NotFound('Endpoint not associated with Project')
        from keystone.identity import controllers as id_controllers
        projects = [self.identity_api.get_project(x.project_id) for x in refs]
        return id_controllers.ProjectV3.wrap_collection(context, projects)
