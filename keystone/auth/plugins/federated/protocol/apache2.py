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

from keystone import exception

from keystone.auth.plugins.federated.protocol import core

'''Passes authentication information from Apache2
   to the core federated module for trust management
'''


class Apache2(core.ProtocolHandler):

    def validate(self, auth_payload):
        uid = auth_payload['protocol_data']["uid"]
        attributes = auth_payload['protocol_data']["user_identity"]
        expiry = auth_payload['protocol_data']["validity_time"]
        return uid, attributes, expiry

    def request_auth(self, auth_payload):
        raise exception.NotImplemented()
