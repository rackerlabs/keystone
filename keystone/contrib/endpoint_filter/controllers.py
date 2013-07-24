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


from keystone.common import controller
from keystone.common import dependency
from keystone.common import wsgi
from keystone.contrib.endpoint_filter import core as ep_filter
from keystone import exception


@dependency.requires('catalog_api', 'identity_api')
class EndpointFilterV3Controller(controller.V3Controller):

    def __init__(self):
        self.ep_filter_api = ep_filter.Manager()
        super(EndpointFilterV3Controller, self).__init__()

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

    def check_ep_filter_association(self, context, project_id, endpoint_id):
        """Verifies endpoint is currently associated with given project."""
        try:
            endpoint = self.catalog_api.get_endpoint(endpoint_id)
            if endpoint is None:
                raise exception.EndpointNotFound

            project = self.identity_api.get_project(project_id)
            if project is None:
                raise exception.ProjectNotFound

            return self.ep_filter_api.check_endpoint_in_project(endpoint_id,
                                                                project_id)
        except exception.ProjectNotFound as pnf:
            raise pnf

    def get_ep_filter_associations(self, context, project_id):
        """Lists all the endpoints currently associated with a give project."""
        project = self.identity_api.get_project(project_id)
        if project is None:
            raise exception.ProjectNotFound

        refs = self.ep_filter_api.list_endpoints_in_project(project_id)
        if refs is None:
            raise exception.NotFound('No Endpoints associated with Project')

        from keystone.catalog import controllers as catalog_controllers
        endpoints = [self.catalog_api.get_endpoint(
            x.endpoint_id) for x in refs]
        return catalog_controllers.EndpointV3.wrap_collection(context,
                                                              endpoints)

    def remove_ep_filter_association(self, context, project_id, endpoint_id):
        """Remove the endpoint fro the association wuth given project."""
        return self.ep_filter_api.remove_ep_filter_association(endpoint_id,
                                                               project_id)

    def list_associated_projects(self, context, endpoint_id):
        """Return a list of projects associated with the endpoint."""
        refs = self.ep_filter_api.list_project_endpoints(endpoint_id)
        if refs is None:
            raise exception.NotFound('Endpoint not associated with Project')
        from keystone.identity import controllers as id_controllers
        projects = [self.identity_api.get_project(x.project_id) for x in refs]
        return id_controllers.ProjectV3.wrap_collection(context, projects)
