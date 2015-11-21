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
"""WSGI Routers for the Trust service."""

from keystone.common import json_home
from keystone.common import wsgi
from keystone.trust import controllers

TRUST_ID_PARAMETER_RELATION = json_home.build_v3_parameter_relation(
    'trust_id', extension_name='OS-TRUST', extension_version='1.0')


class Routers(wsgi.RoutersBase):

    def _add_resource(self, *args, **kwargs):
        kwargs.setdefault('extension_name', 'OS-TRUST')
        kwargs.setdefault('extension_version', '1.0')
        return super(Routers, self)._add_resource(*args, **kwargs)

    def append_v3_routers(self, mapper, routers):
        trust_controller = controllers.TrustV3()

        self._add_resource(
            mapper, trust_controller,
            path='/OS-TRUST/trusts',
            get_action='list_trusts',
            post_action='create_trust',
            rel='trusts')
        self._add_resource(
            mapper, trust_controller,
            path='/OS-TRUST/trusts/{trust_id}',
            get_action='get_trust',
            delete_action='delete_trust',
            rel='trust',
            path_vars={
                'trust_id': TRUST_ID_PARAMETER_RELATION,
            })
        self._add_resource(
            mapper, trust_controller,
            path='/OS-TRUST/trusts/{trust_id}/roles',
            get_action='list_roles_for_trust',
            rel='trust_roles',
            path_vars={
                'trust_id': TRUST_ID_PARAMETER_RELATION,
            })
        self._add_resource(
            mapper, trust_controller,
            path='/OS-TRUST/trusts/{trust_id}/roles/{role_id}',
            get_head_action='get_role_for_trust',
            rel='trust_role',
            path_vars={
                'trust_id': TRUST_ID_PARAMETER_RELATION,
                'role_id': json_home.Parameters.ROLE_ID,
            })
