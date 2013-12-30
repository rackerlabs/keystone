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

from keystone import assignment
from keystone import auth
from keystone import exception
from keystone import identity

from keystone.common import config

from keystone.openstack.common import importutils
from keystone.openstack.common import log as logging

from keystone.auth.plugins.federated import user_management

METHOD_NAME = "federated"

CONF = config.CONF
LOG = logging.getLogger(__name__)

PROTOCOLS = {}


def load_auth_protocol(protocol_name):
    if protocol_name not in CONF.auth.protocols:
        raise exception.Unauthorised("Auth Protocol not supported")
    driver = CONF.auth.get(protocol_name)
    return importutils.import_object(driver)


def get_auth_protocol(protocol_name):
    global PROTOCOLS
    if protocol_name not in PROTOCOLS:
        PROTOCOLS[protocol_name] = load_auth_protocol(protocol_name)
    return PROTOCOLS[protocol_name]


class Federated(auth.AuthMethodHandler):

    def __init__(self):
        self.discovery_driver = importutils.import_object(
            CONF.auth.get("discovery"))
        self.mapping = importutils.import_object(
            CONF.auth.get("attribute_mapper"))
        self.issuing = importutils.import_object(
            CONF.auth.get("issuing_policy"))

    def authenticate(self, context, auth_payload, auth_context):
        '''Authenticate the user, auth_payload should contain:
           protocol - the protocol the identity provider uses
           provider_id - an identifier for the identity provider
           assertion - an authentication assertion to be validated
        '''
        # Grab the phase parameter
        phase = auth_payload.get("phase", None)
        msg = ("Federated Requests must specify which"
               "stage of authentication has been reached")
        if not phase:
            return msg
        try:
            phase_function = getattr(self, phase)
        except AttributeError as e:
            return "Authentication phase not supported: " + e.message
        response = phase_function(auth_payload)
        if response.get("response") is not None:
            return response.get("response")
        else:
            self.identity_api = identity.Manager()
            self.assignment_api = assignment.Manager()
            valid_attributes = {}
            user_man = user_management.UserManager()
            auth_context["user_id"] = user_man.manage(response["uid"])
            for attribute_set in response["user_identity"]:
                attributes = attribute_set.get("attributes", None)
                provider = attribute_set.get("provider", None)
                validated = self.issuing.check_issuers(attributes,
                                                       provider)
                for v in validated:
                    valid_attributes.update(v)
            auth_context["attributes"] = self.mapping.map(valid_attributes)
            auth_context["extras"]["projects"] = []
            for att in auth_context["attributes"]:
                for role in att["role"]:
                    for project in att["project"]:
                        p = self.assignment_api.get_project(project)
                        auth_context["extras"]["projects"].append(p)
                        self.assignment_api.create_grant(
                            role,
                            auth_context["user_id"],
                            project_id=project)
        return

    def discovery(self, auth_payload):
        '''Return a list of available Identity Providers.'''
        return {"response": self.discovery_driver.get_directory()}

    def request(self, auth_payload):
        '''Create an authentication request for the provider in the auth
           payload. If a provider is not specified the return error message
           raise Exception
        '''

        if not auth_payload.get("provider_id", None):
            raise exception.NotFound("Missing Provider ID")
        self.discovery_driver.populate_auth_dict(auth_payload,
                                                 auth_payload.get(
                                                     "provider_id"))
        protocol = auth_payload.get("protocol", None)
        response = get_auth_protocol(protocol).request_auth(auth_payload)
        return {"response": response}

    def validate(self, auth_payload):
        '''Validate the response in a protocol appropriate manner
            and return the user ID, attributes and the validity of
            the validated response
        '''
        if not auth_payload.get("provider_id"):
            raise exception.NotFound("Missing Provider ID")
        resp = {"response": None}
        self.discovery_driver.populate_auth_dict(auth_payload,
                                                 auth_payload.get(
                                                     "provider_id"))
        if not auth_payload.get("protocol"):
            return {"response": "Protocol not found or not recognised"}

        protocol = get_auth_protocol(auth_payload["protocol"])

        uid, user_identity, validity_time = protocol.validate(auth_payload)
        resp['uid'] = uid
        resp['user_identity'] = user_identity
        resp['validity_time'] = validity_time
        return resp
