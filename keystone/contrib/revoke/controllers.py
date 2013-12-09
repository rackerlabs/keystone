# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack Foundation
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


@dependency.requires('revoke_api')
class RevokeController(controller.V3Controller):

#    @controller.protected()
    def describe(self, context):
        """Description of the controller logic."""
        container = {"revoke": ""}
        container['links'] = {
            'next': None,
            'self': RevokeController.base_url(path=context['path']),
            'revoked_tokens': RevokeController.base_url(
                path=context['path'] + "/revoked_tokens"),
            'previous': None}
        return container

    @controller.protected()
    def get_revocation_events(self, filter):
        """Description of the controller logic."""
        self.revoke_api.get_revoked_tokens(filter)

    @controller.protected()
    def revoke_by_expiration(self, user_id, expires_at):
        self.revoke_api.revoke_by_user(self, user_id)

    @controller.protected()
    def revoke_by_user(self, user_id):
        self.revoke_api.revoke_by_user(self, user_id)

    @controller.protected()
    def revoke_by_domain(self, domain_id):
        self.revoke_api.revoke_by_domain(self, domain_id)

    @controller.protected()
    def revoke_by_project(self, project_id):
        self.revoke_api.revoke_by_project(project_id)

    @controller.protected()
    def revoke_by_trust(self, trust_id):
        self.revoke_api.revoke_by_trust(trust_id)
