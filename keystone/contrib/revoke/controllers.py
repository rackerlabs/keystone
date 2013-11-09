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


@dependency.requires('example_api')
class ExampleV3Controller(controller.V3Controller):

    @controller.protected()
    def get(self):
        """Description of the controller logic."""
        self.revoke_api.get_revoked_tokens()

    @controller.protected()
    def revoke_token(self, token):
        """Description of the controller logic."""
        self.revoke_api.get_revoked_tokens(context)

    def revoke_by_scope(self, revocation_event):
        """Description of the controller logic."""
        self.revoke_api.get_revoked_tokens(context)

