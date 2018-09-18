#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

# This file handles all flask-restful resources for /v3/domains

import flask
import flask_restful
from six.moves import http_client

from keystone.common import json_home
from keystone.common import provider_api
from keystone.common import rbac_enforcer
from keystone.common import validation
import keystone.conf
from keystone import exception
from keystone.resource import schema
from keystone.server import flask as ks_flask

CONF = keystone.conf.CONF
ENFORCER = rbac_enforcer.RBACEnforcer
PROVIDERS = provider_api.ProviderAPIs


class ProjectResource(ks_flask.ResourceBase):
    collection_key = 'projects'
    member_key = 'projects'
    get_member_from_drive = PROVIDERS.deferred_provider_lookup(
        api='resource_api', method='get_project')

    def _get_project(self, project_id):
        ENFORCER.enforce_call(action='identity:get_project')
        return self.wrap_member(PROVIDERS.resource_api.get_project(project_id))

    def _list_projects(self):
        # TODO: figure out the hints.
        #  - What are the defaults?
        #  - How do we determine the 'tag_params' within the request context?
        filters = []
        ENFORCER.enforce_call(action='identity:list_projects',
                              filters=filters)
        hints = self.build_driver_hints(filters)
        refs = PROVIDERS.resource_api.list_projects(hints=hints)
        return ProjectV3.wrap_collection(refs, hints=hints)

    def get(self, project_id=None):
        """Get project or list projects.

        GET/HEAD /v3/projects
        GET/HEAD /v3/projects/{project_id}
        """
        if project_id is not None:
            return self._get_project(self, project_id)
        else:
            return self._list_projects()

    def post(self):
        """Create project.

        POST /v3/projects
        """
        # TODO(hrybacki) ask Morgan if it makes more sense to validate
        # the payload prior to calling the enforcer
        ENFORCER.enforce_call(action='identity:create_project')
        project = self.request_body_json.get('project', {})
        validation.lazy_validate(schema.project_create, project)
        project = self._assign_unique_id(project)
        project = self._normalize_dict(project)
        ref = PROVIDERS.resource_api.create_project(
            project['id'],
            project,
            initiator=self.audit_initiator)
        return self.wrap_member(ref), http_client.CREATED

    def patch(self, project_id):
        """Update project.

        PATCH /v3/projects/{project_id}
        """
        ENFORCER.enforce_call(action='identity:update_project')
        project = self.request_body_json.get('project', {})
        validation.lazy_validate(schema.project_update, project)
        PROVIDERS.resource_api.get_project(project_id)
        # TODO(hrybacki) Do we need to ensure that the project_id
        # and project['id'] are matching explicitly?
        ref = PROVIDERS.resource_api.update_project(
            project_id,
            project,
            initiator=self.audit_initiator)
        return self.wrap_member(ref)

    def delete(self, project_id):
        """Delete project.

        DELETE /v3/projects/{project_id}
        """
        ENFORCER.enforce_call(action='identity:delete_project')
        PROVIDERS.resource_api.delete_project(
            project_id,
            initiator=self.audit_initiator)
        return None, http_client.NO_CONTENT


class ProjectTagsResource(ks_flask.ResourceBase):
    member_key = 'config'
    collection_key = 'config'

    def get(self, project_id):
        """List tags associated with a given project

        GET /v3/projects/{project_id}/tags
        """
        ENFORCER.enforce_call(action='identity:list_project_tags')
        ref = PROVIDERS.resource_api.list_project_tags(project_id)
        return self.wrap_member(ref)

    def put(self, project_id):
        """Update all tags associated with a given project

        PUT /v3/projects/{project_id}/tags
        """
        ENFORCER.enforce_call(action='identity:update_project_tags')
        tags = self.request_body_json.get('tags', {})
        ref = PROVIDERS.resource_api.update_project_tags(
            project_id, tags, initiator=request.audit_initiator)
        return self.wrap_member(ref)


# class ProjectTagResource(ks_flask.ResourceBase):
#     member_key = 'config'
#     collection_key = 'config'
#
#     def get(self, project_id, value):
#         """Get information for a single tag associated with a given project
#
#         GET /v3/projects/{project_id}/tags/{value}
#         """
#         ENFORCER.enforce_call(action='identity:get_project_tags')
#         PROVIDERS.resource_api.get_project_tag(project_id, value)


class ProjectAPI(ks_flask.APIBase):
    CONFIG_GROUP = json_home.build_v3_parameter_relation('config_group')
    CONFIG_OPTION = json_home.build_v3_parameter_relation('config_option')
    _name = 'projects'
    _import_name = __name__
    # TEMP(hrybacki) Note that `resources` handles special logic for json-home
    resources = [ProjectResource]
    resource_mapping = [
        ks_flask.construct_resource_map(
            resource=ProjectTagsResource,
            url=('/projects/<string:project_id>/tags'),
            resource_kwargs={},
            rel='project_tags',  # what is this params relation to the resource map?
            path_vars={
                'project_id': json_home.Parameters.PROJECT_ID}),
    ]


APIs = (ProjectAPI,)
