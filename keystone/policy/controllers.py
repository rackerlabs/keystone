# Copyright 2012 OpenStack Foundation
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

from keystone.api.views.v3 import policy as policy_view
from keystone.common import controller
from keystone.common import dependency
from keystone.common import validation
from keystone.policy import schema


@dependency.requires('policy_api')
class PolicyV3(controller.V3Controller):
    collection_name = 'policies'
    member_name = 'policy'

    @controller.protected()
    def create_policy(self, request, policy):
        validation.lazy_validate(schema.policy_create, policy)
        ref = self._assign_unique_id(self._normalize_dict(policy))
        ref = self.policy_api.create_policy(ref['id'],
                                            ref,
                                            initiator=request.audit_initiator)
        return policy_view.PolicyView(request).create(ref)

    @controller.filterprotected('type')
    def list_policies(self, request, filters):
        hints = self.build_driver_hints(request, filters)
        refs = self.policy_api.list_policies(hints=hints)
        return self.render_list(policy_view.PolicyView(request), refs, hints)

    @controller.protected()
    def get_policy(self, request, policy_id):
        ref = self.policy_api.get_policy(policy_id)
        return policy_view.PolicyView(request).show(ref)

    @controller.protected()
    def update_policy(self, request, policy_id, policy):
        validation.lazy_validate(schema.policy_update, policy)
        ref = self.policy_api.update_policy(policy_id,
                                            policy,
                                            initiator=request.audit_initiator)
        return policy_view.PolicyView(request).show(ref)

    @controller.protected()
    def delete_policy(self, request, policy_id):
        self.policy_api.delete_policy(policy_id,
                                      initiator=request.audit_initiator)
        return policy_view.PolicyView(request).delete(policy_id)
