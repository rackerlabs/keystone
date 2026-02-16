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

from oslo_context import context as oslo_context

from keystone import exception
from keystone.i18n import _
from keystone.trust.backends import sql


class Trust(sql.Trust):
    def _ensure_create_trust_allowed(self, trust):
        request_context = oslo_context.get_current()
        print("LEKKAHHH")
        print("LEKKAHHH")
        print("LEKKAHHH")
        print("LEKKAHHH")
        print("LEKKAHHH")
        if request_context and request_context.user_id != trust.get(
            'trustor_user_id'
        ):
            if (request_context.is_admin is True) or (
                "admin" in request_context.roles
            ):
                return
            action = _("The authenticated user should match the trustor")
            raise exception.ForbiddenAction(action=action)
