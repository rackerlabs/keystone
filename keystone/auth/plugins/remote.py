# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack LLC
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


from keystone import auth
from keystone import config
from keystone import exception

from keystone.auth.plugins import common
from keystone.common import logging
from keystone import identity


METHOD_NAME = 'remote'

LOG = logging.getLogger(__name__)

CONF = config.CONF


class RemoteUser(auth.AuthMethodHandler):
    def __init__(self):
        self.method_name = METHOD_NAME

    def authenticate(self, context, auth_payload, user_context, method_names):
        identity_api = identity.Manager()
        if 'REMOTE_USER' in context:
            user_name = context['REMOTE_USER']
            domain_ref = (common.lookup_domain
                          (context,
                           {'id': CONF.identity.default_domain_id},
                           identity_api))
            try:
                user_ref = identity_api.get_user_by_name(
                    context=context, user_name=user_name,
                    domain_id=domain_ref['id'])
                user_context['user_id'] = user_ref['id']
            except exception.UserNotFound:
                pass
        return
