# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Red Hat, Inc.
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

from keystone.common import dependency
from keystone.common import wsgi


@dependency.requires('identity_api', 'kds_api', 'policy_api', 'token_api')
class KDSController(wsgi.Application):
    def get_info(self, context):
        return {'version': '0.0.1'}

    def get_ticket(self, context, request):
        return self.kds_api.get_ticket(context, request)

    def set_key(self, context, request):
        self.assert_admin(context)
        return self.kds_api.set_key(context, request)
