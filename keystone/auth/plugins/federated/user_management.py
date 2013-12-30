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

import base64
import hashlib
import random
import time

from keystone import exception
from keystone import identity


temp_password = str(random.getrandbits(20))
temp_password = str(time.time()) + temp_password
sha = hashlib.sha1()
sha.update(temp_password)
temp_password = base64.b64encode(sha.digest())


class UserManager(object):

    def __init__(self):
        self.identity_api = identity.controllers.UserV3()

    def manage(self, username):
        # Create User
        sha1 = hashlib.sha1()
        sha1.update(username)
        new_id = base64.b64encode(sha1.digest())
        tempPass = temp_password
        user_ref = {'id': new_id, 'name': new_id, 'password': tempPass}
        try:
            user = self.identity_api.create_user(
                {'is_admin': True},
                user=user_ref)['user']
            return user['id']
        except exception.Conflict:
            users = self.identity_api.list_users(
                {"is_admin": True, "query_string": {}, "path": "/"})
            for u in users["users"]:
                if new_id == u["name"]:
                    user = u
        # Return user
            return user["id"]
