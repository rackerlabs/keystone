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

from oslo_serialization import jsonutils

from keystone.common import controller
from keystone.common import dependency
from keystone.common import validation
from keystone.limit import schema
from keystone import exception
from keystone.i18n import _

@dependency.requires('registered_limit_api')
class RegisteredLimitV3(controller.V3Controller):
    collection_name = 'registered_limits'

    def __init__(self):
        super(RegisteredLimitV3, self).__init__()
        self.get_member_from_driver = self.registered_limit_api.get_registered_limit

    @controller.protected()
    def create_registered_limits(self, request, registered_limits):
        assert(isinstance(registered_limits, list))
        for registered_limit in registered_limits:
            validation.lazy_validate(schema.registered_limit_create_or_update, registered_limit)
        refs = self.registered_limit_api.create_registered_limits([self._normalize_dict(registered_limit) for registered_limit in registered_limits])
        return {self.collection_name: refs} #TODO: these should all use controller.wrap_member/wrap_collection

    @controller.filterprotected('service_type', 'region', 'resource_name')
    def list_registered_limits(self, request, filters):
        hints = RegisteredLimitV3.build_driver_hints(request, filters)
        refs = self.registered_limit_api.list_registered_limits(hints)
        return {self.collection_name: refs}

    def update_registered_limits(self, request, registered_limits):
        assert(isinstance(registered_limits, list))
        for registered_limit in registered_limits:
            validation.lazy_validate(schema.registered_limit_create_or_update, registered_limit)
        refs = self.registered_limit_api.update_registered_limits([self._normalize_dict(registered_limit) for registered_limit in registered_limits])
        return {self.collection_name: refs}

    def delete_registered_limits(self, request, registered_limits):
        return self.registered_limit_api.delete_registered_limits(registered_limits)


@dependency.requires('limit_api')
class LimitV3(controller.V3Controller):
    collection_name = 'limits'

    def __init__(self):
        super(LimitV3, self).__init__()
        self.get_member_from_driver = self.limit_api.get_limit

    @controller.protected()
    def create_or_update_limits(self, request, project_id, limits):
        assert(isinstance(limits, list))
        for limit in limits:
            validation.lazy_validate(schema.limit_create_or_update, limit)
        refs = self.limit_api.create_or_update_limits(project_id, [self._normalize_dict(limit) for limit in limits])
        return {self.collection_name: refs}

    @controller.filterprotected('service_type', 'region', 'resource_name')
    def list_limits(self, request, filters, project_id):
        hints = LimitV3.build_driver_hints(request, filters)
        refs = self.limit_api.list_limits(project_id, hints)
        return {self.collection_name: refs}

    def delete_limits(self, request, limits):
        return self.limit_api.delete_limits(limits)
