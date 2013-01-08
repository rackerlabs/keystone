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

from keystone import exception
from keystone.common import dependency


@dependency.requires('identity_api')
class AuthMethodHandler(object):
    """Abstract base class for an authentication plugin."""

    def __init__(self):
        pass

    def authenticate(self, context, auth_info, auth_context):
        """ Authenticate user and return an authentication context.

        :param context: keystone context
        :auth_info: keystone.auth.controller.AuthInfo object, encapsulates
                    "auth" data
        :auth_context: user authentication context, a dictionary shared
                       by all plugins

        If success, auth plugin must provide a valid "user_id" in
        auth_context. Auth plugin may optionally add any addition methods
        into the "method_names"
        list. For example, if the authentiation is for rescoping, auth method
        must append the previous method names into "method_names". Also, auth
        plugin may add any addition information into the "extras" dictionary
        in the auth_context. Anything in "extras" will be conveyed in the
        token's extras field.

        :returns: None if authenticaiton is successful.
                  Authentication payload for the next authentication step if
                  this is a multi-roundtrip authentication.
        :raises: exception.Unauthorized for authenticaiton failure.

        """
        raise exception.Unauthorized()
