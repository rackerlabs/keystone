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

from keystone.common import provider_api
from keystone import exception
from keystone.i18n import _
from keystone.limit.model import base

LOG = log.getLogger(__name__)
PROVIDERS = provider_api.ProviderAPIs


class TwoLevelHierarchyModel(base.ModelBase):

    def __init__(self):
        self.project = []

    def calculate_limit(self, limit, parent_project):
        check_fail = False
        limits = PROVIDERS.unified_limit_api.get_project_limit(parent_project)
        if limit['resource_limit'] > limits['resource_limit']:
            check_fail = True
        if check_fail:
            error = _()
            raise exception.LimitCheckError(error=error)

    def check_limit(self, limit, project):
        parent_project = project['parent_id']
        if parent_project:
            try:
                self.calculate_limit(limit, parent_project)
            except exception.LimitCheckError as e:
                LOG(e)
                if limit.get('region_id'):
                    reason = _("The limit %(resource_limit)s for resource "
                               "%(resource_name)s, %(service_id)s and "
                               "%(region_id)s doesn't satisfy current limit "
                               "model.") % {'resource_limit': 111,
                                            'resource_name': 222,
                                            'service_id': 333,
                                            'region_id': 444}
                else:
                    reason = _("The limit %(resource_limit)s for resource "
                               "%(resource_name)s and %(service_id)s doesn't "
                               "satisfy current limit model.") % {'resource_limit': 111,
                                                                  'resource_name': 222,
                                                                  'service_id': 333}
                raise exception.InvalidLimit(reason=reason)
