# Copyright 2018 Huawei
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

from oslo_log import log

from keystone.common import driver_hints
from keystone.common import provider_api
from keystone import exception
from keystone.i18n import _
from keystone.limit.models import base

LOG = log.getLogger(__name__)
PROVIDERS = provider_api.ProviderAPIs


class Model(base.ModelBase):
    NAME = 'strict_two_level'
    DESCRIPTION = (
        'strict two level hierarchical limit.'
    )
    MIX_PROJECT_TREE_DEPTH = 2

    def _get_specified_limit(self, project_id, resource_name, service_id,
                             region_id, is_parent=True):
        hints = driver_hints.Hints()
        hints.add_filter('project_id', project_id)
        hints.add_filter('service_id', service_id)
        hints.add_filter('resource_name', resource_name)
        hints.add_filter('region_id', region_id)
        limit = PROVIDERS.unified_limit_api.list_limits(hints)
        if not limit and is_parent:
            hints = driver_hints.Hints()
            hints.add_filter('service_id', service_id)
            hints.add_filter('resource_name', resource_name)
            hints.add_filter('region_id', region_id)
            limit = PROVIDERS.unified_limit_api.list_registered_limits(hints)
        return limit

    def _check_limit(self, project_id, resource_name, resource_limit,
                     service_id, region_id, parent_id):
        if parent_id:
            parent_limit = self._get_specified_limit(
                parent_id, resource_name, service_id, region_id)
            if parent_limit:
                if not resource_limit <= parent_limit['resource_limit']:
                    raise exception.InvalidLimit()

        sub_projects = PROVIDERS.resource_api.list_projects_in_subtree(
            project_id)
        for sub_project in sub_projects:
            sub_limit = self._get_specified_limit(
                sub_project['id'], resource_name, service_id, region_id,
                is_parent=False)
            if sub_limit:
                if not resource_limit >= sub_limit['resource_limit']:
                    raise exception.InvalidLimit()

    def check_limit_hierarchy(self, limits):
        limit_mapping = {}
        for limit in limits:
            limit_mapping[
                (limit['project_id'],
                 limit['resource_name'],
                 limit['service_id'],
                 limit.get('region_id'))] = limit['resource_limit']

        for limit in limits:
            project_id = limit['project_id']
            resource_name = limit['resource_name']
            resource_limit = limit['resource_limit']
            service_id = limit['service_id']
            region_id = limit.get('region_id')
            try:
                project = PROVIDERS.resource_api.get_project(project_id)
                parent_id = project.get('parent_id')
                parent_limit = limit_mapping.get(
                    (parent_id, resource_name, service_id, region_id))

                if parent_limit and resource_limit > parent_limit:
                    raise exception.InvalidLimit()

                self._check_limit(project_id, resource_name, resource_limit,
                                  service_id, region_id, parent_id)
            except exception.InvalidLimit:
                if region_id:
                    error = _("The input (project %(project_id)s, "
                              "resource_name %(resource_name)s, "
                              "resource_limit %(resource_limit)s, "
                              "service %(service_id)s, "
                              "region_id %(region_id)s) doesn't satisfy "
                              "current hierarchy model.") % {
                        'project_id': project_id,
                        'resource_name': resource_name,
                        'resource_limit': resource_limit,
                        'service_id': service_id,
                        'region_id': region_id
                    }
                else:
                    error = _("The input (project %(project_id)s, "
                              "resource_name %(resource_name)s, "
                              "resource_limit %(resource_limit)s, "
                              "service %(service_id)s, doesn't satisfy "
                              "current hierarchy model.") % {
                        'project_id': project_id,
                        'resource_name': resource_name,
                        'resource_limit': resource_limit,
                        'service_id': service_id
                    }
                LOG(error)
                raise exception.InvalidLimit(reason=error)
