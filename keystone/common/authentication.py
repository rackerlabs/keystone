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
import uuid

from keystone import exception


_AUTH_CHECK_ATTR = uuid.uuid4().hex
_ERR = uuid.uuid4().hex


class AuthEnforcer(object):
    """Enforce Auth on API Calls."""

    __shared_state = {}

    def __init__(self):
        self.__dict__ = self.__shared_state__

    @classmethod
    def authorize_call(cls):
        """Enforce authorization on the current request."""
        auth_pass = getattr(flask.g, _AUTH_CHECK_ATTR, False)
        if not auth_pass:
            err = getattr(flask.g, _ERR, None)
            raise exception.Unauthorized(err)
