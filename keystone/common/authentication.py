#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import flask

from keystone import exception


_AUTH_CHECK_ATTR = 'keystone:auth:pass'


class AuthEnforcer(object):
    """Enforce Auth on API Calls."""

    __shared_state = {}
    ACTION_STORE_ATTR = 'keystone:auth:pass'

    def __init__(self):
        self.__dict__ = self.__shared_state__

    def authorize_call(cls, action=None):
        """Enforce authorization on the current request."""
        action = action or getattr(flask.g, cls.ACTION_STORE_ATTR, False)

        if not action:
            raise exception.Unauthorized()
