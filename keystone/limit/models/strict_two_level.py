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

import copy

from oslo_log import log

from keystone.common import driver_hints
from keystone.common import provider_api
from keystone import exception
from keystone.limit.models import base

LOG = log.getLogger(__name__)
PROVIDERS = provider_api.ProviderAPIs


class StrictTwoLevelModel(base.ModelBase):
    NAME = 'strict_two_level'
    DESCRIPTION = (
        'This model requires project hierarchy never exceeds a depth of two'
    )
    MAX_PROJECT_TREE_DEPTH = 2

    def check_limit(self, project_id, resource_name, resource_limit,
                    service_id, region_id=None):
        # build a common hints instance since we'll need it later and this
        # reduces defining it multple times
        hints = driver_hints.Hints()
        hints.add_filter('service_id', service_id)
        hints.add_filter('resource_name', resource_name)
        if region_id:
            hints.add_filter('region_id', region_id)

        if self._has_parent_project(project_id):
            # get either the parent limit or the registered limit
            parent_project_id = self._get_parent_project_id(project_id)

            parent_limit = self._get_project_limit_value(
                parent_project_id, copy.deepcopy(hints)
            )
            if not parent_limit:
                parent_limit = self._get_registered_limit_value(hints)

            # if a child project, make sure it doesn't exceed the parent limit
            if parent_limit < resource_limit:
                raise exception.InvalidLimit(
                    reason="Limit exceeds the limit of the parent"
                )
        else:
            # elif a parent limit, ensure it exceeds the limits of the children
            child_projects = PROVIDERS.resource_api.list_projects_in_subtree(
                project_id)
            for child in child_projects:
                child_limit = self._get_project_limit_value(
                    child['id'], copy.deepcopy(hints)
                )
                if not child_limit:
                    child_limit = self._get_registered_limit_value(hints)

                if resource_limit < child_limit:
                    raise exception.InvalidLimit(
                        reason="Limit is smaller than child")

    def _has_parent_project(self, project_id):
        parent = PROVIDERS.resource_api.list_project_parents(project_id)[0]
        if parent.get('is_domain'):
            return False
        return True

    def _get_parent_project_id(self, project_id):
        parent = PROVIDERS.resource_api.list_project_parents(project_id)[0]
        return parent['id']

    def _get_project_limit_value(self, project_id, hints):
        hints.add_filter('project_id', project_id)
        limits = PROVIDERS.unified_limit_api.list_limits(hints)
        if limits:
            return limits[0]['resource_limit']

    def _get_registered_limit_value(self, hints):
        limits = PROVIDERS.unified_limit_api.list_registered_limits(hints)
        limit_value = limits[0]['default_limit']
        return limit_value
