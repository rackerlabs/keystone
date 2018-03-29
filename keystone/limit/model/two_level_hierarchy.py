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
from keystone.limit.model import base

LOG = log.getLogger(__name__)
PROVIDERS = provider_api.ProviderAPIs


class TwoLevelHierarchyModel(base.ModelBase):

    def __init__(self):
        self.project = []

    def _calculate_limit(self, limits):
        # TODO(wxy) add the check logic
        check_fail = False
        # hierarchy_deep = 1
        # parent_project_id = project['parent_id']
        # parent_project = PROVIDERS.resource_api.get_project(parent_project_id)
        # if parent_project.get('parent_id'):
        #     LOG.error(_("The project level is not two"))
        #     check_fail = True
        # hints = driver_hints.Hints()
        # hints.add_filter('project_id', parent_project_id)
        # hints.add_filter('service_id', limit['service_id'])
        # hints.add_filter('region_id', limit.get('region_id'))
        # parent_limit = PROVIDERS.unified_limit_api.list_limits(hints)
        # if not parent_limit:
        #
        # if limit['resource_limit'] > parent_limit['resource_limit']:
        #     check_fail = True
        return check_fail

    def check_limit(self, limits):

        fail = self._calculate_limit(limits)
        if fail:
            error = _()
            LOG(error)
            raise exception.InvalidLimit(reason=error)
