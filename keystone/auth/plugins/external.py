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

"""Keystone External Authentication Plugin"""

from keystone import exception


class External(object):
    def authenticate(self, context, auth_info, auth_context):
        username = context['REMOTE_USER']
        # FIXME(gyee): REMOTE_USER is not good enough since we are
        # requiring domain_id to do user lookup now. Try to get
        # the user_id from auth_info for now, assuming external auth
        # has check to make sure user is the same as the one specify
        # in "identity".
        if 'password' in auth_info.get_method_names():
            user_info = auth_info.get_method_data('password')
            user_ref = auth_info.lookup_user(user_info['user'])
            auth_context['user_id'] = user_ref['id']
            
            if ('kerberos' in CONF.token.bind and 
                context.get('AUTH_TYPE', '').lower() == 'negotiate'):
                auth_context['bind']['kerberos'] = username
        else:
            msg = _('Unable to lookup user %s') % (username)
            raise exception.Unauthorized(msg)
