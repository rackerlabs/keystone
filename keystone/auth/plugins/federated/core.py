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
import json
import random
import time

from keystone import assignment
from keystone import auth
from keystone import catalog
from keystone import exception
from keystone import identity

from keystone.common import config

from keystone.openstack.common import log as logging


METHOD_NAME = "federated"

CONF = config.CONF
LOG = logging.getLogger(__name__)


class FederatedHandler(auth.AuthMethodHandler):

    def __init__(self):
        # replace handlers with API based versions
        self.mapping = SimpleFileBasedMapper()
        self.issuing = SimpleFileBasedIssuingPolicy()
        self.discovery_service = Discovery()
        self.user_management = UserManager()

    def authenticate(self, context, auth_payload, auth_context):
        '''Authenticate the user, auth_payload should contain:
           provider_id - an identifier for the identity provider
           phase - the current authentication phase reached
           protocol_data - an authentication assertion to be validated
        '''
        # Grab the phase parameter
        phase = auth_payload.get("phase", None)
        msg = ("Federated Authentication Requests must specify which"
               "stage of authentication has been reached")
        if not phase:
            return msg
        try:
            phase_function = getattr(self, phase)
        except AttributeError as e:
            return "Authentication phase not supported: " + e.message
        response = phase_function(auth_payload)
        if response.get("response") is not None:
            '''If a response is returned then authentication is not yet
               complete, so return the response to the auth module'''
            return response.get("response")
        else:
            self.identity_api = identity.Manager()
            self.assignment_api = assignment.Manager()
            valid_attributes = {}
            auth_context["user_id"] = self.user_management.manage(
                response["uid"])
            for attribute_set in response["user_identity"]:
                attributes = attribute_set.get("attributes", None)
                provider = attribute_set.get("provider", None)
                validated = self.issuing.check_issuers(attributes,
                                                       provider)
                valid_attributes.update(validated)
            auth_context["attributes"] = self.mapping.map(valid_attributes,
                                                          provider)
            auth_context["extras"]["projects"] = []
            for att in auth_context["attributes"]:
                for role in att["roles"]:
                    for project in att["projects"]:
                        p = self.assignment_api.get_project(project)
                        auth_context["extras"]["projects"].append(p)
                        self.assignment_api.create_grant(
                            role,
                            auth_context["user_id"],
                            project_id=project)
        return

    def discovery(self, auth_payload):
        return {"response": self.discovery_service.get_directory()}

    def request(self, auth_payload):
        raise exception.NotImplemented

    def validate(self, auth_payload):
        raise exception.NotImplemented


class Discovery(object):

    def __init__(self):
        '''Constructor.'''
        self.catalog_api = catalog.controllers.ServiceV3()
        self.endpoint_api = catalog.controllers.EndpointV3()

    def get_directory(self):
        '''Return services which match idp.*
           from the service catalog.
        '''
        return self.format_directory(
            self.catalog_api.list_services(
                {"is_admin": True, "query_string": {}, "path": "/"}))

    def populate_auth_dict(self, federated, provider):
        '''Populate the given federated dict with validation
           and endpoint data for the specified provider.
        '''
        endpoints = self.endpoint_api.list_endpoints(
            {"is_admin": True, "query_string": {}, "path": "/"})
        service = self.catalog_api.get_service(
            {"is_admin": True}, provider)["service"]
        for endpoint in endpoints["endpoints"]:
            if not endpoint["interface"] == "public":
                endpoints["endpoints"].pop(
                    endpoints["endpoints"].index(endpoint))
            elif endpoint["service_id"] == service["id"]:
                validation = endpoint.get("validation", None)
                federated["validation"] = validation
                endpoint_url = endpoint["url"]
                federated["endpoint"] = endpoint_url
        federated["protocol"] = service["type"].split(".")[1]

    def format_directory(self, services):
        '''Format the list of services to exclude
           non-identity-provider services.
        '''
        providers = []
        endpoints = self.endpoint_api.list_endpoints(
            {"is_admin": True, "query_string": {}, "path": "/"})
        for service in services["services"]:
            if service["type"].startswith("idp"):
                for endpoint in endpoints["endpoints"]:
                    if not endpoint["interface"] == "public":
                        endpoints["endpoints"].pop(
                            endpoints["endpoints"].index(endpoint))
                    elif endpoint["service_id"] == service["id"]:
                        providers.append(service)
        return {"providers": providers}


class SimpleFileBasedMapper(object):

    def __init__(self):
        mapping_file = CONF.federated.get("mapping_file")
        self.mappings = json.load(open(mapping_file))

    def map(self, attributes, provider_id):
        valid_attributes = []
        mappings = self.mappings.get(provider_id)
        for mapping in mappings:
            requirement = mapping.get("requirement", "any_one_of")
            external = mapping.get("external")
            internal = mapping.get("internal")
            if requirement == "any_one_of":
                valid = True
                for att in external:
                    received = attributes.get(att)
                    if not received:
                        valid = False
                    else:
                        found = False
                        for value in received:
                            if value in external.get(att):
                                found = True
                        if not found:
                            valid = False
                if valid:
                    valid_attributes.append(internal)

            if requirement == "not_any_of":
                valid = False
                for att in external:
                    received = attributes.get(att)
                    if not received:
                        valid = False
                    else:
                        found = False
                        for value in received:
                            if value in external.get(att):
                                found = True
                        if not found:
                            valid = True
                if valid:
                    valid_attributes.append(internal)
            if requirement == "all_of":
                valid = True
                for att in external:
                    received = attributes.get(att)
                    if not received:
                        valid = False
                    else:
                        found = True
                        for value in external.get(att):
                            if value not in received:
                                found = False
                        if not found:
                            valid = False
                if valid:
                    valid_attributes.append(internal)
        return valid_attributes


class SimpleFileBasedIssuingPolicy(object):

    def __init__(self):
        policy = CONF.federated.get("issuing_policy_file")
        self.issuing_policy = json.load(open(policy))

    def check_issuers(self, attributes, provider_id):
        policy = self.issuing_policy.get(provider_id, None)
        if not policy:
            raise exception.Unauthorized
        validated = {}
        for att_type in attributes:
            values = attributes.get(att_type, None)
            att = policy.get(att_type, None)
            if att is not None:
                if len(att) == 0:
                    validated[att_type] = values
                else:
                    valid_values = []
                    for value in values:
                        if value in att:
                            valid_values.append(value)
                    validated[att_type] = valid_values
        return validated

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
                {"is_admin": True}, user=user_ref)['user']
            return user['id']
        except exception.Conflict:
            users = self.identity_api.list_users(
                {"is_admin": True, "query_string": {}, "path": "/"})
            for u in users["users"]:
                if new_id == u["name"]:
                    user = u
        # Return user
            return user["id"]
