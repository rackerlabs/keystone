'''
Created on 7 Jun 2013

@author: kwss
'''

from keystone import auth
from keystone import exception
from keystone import identity
from keystone import assignment
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
        raise exception.AuthProtocolNotSupported()
    driver = CONF.auth.get(protocol_name)
    return importutils.import_object(driver)


def get_auth_protocol(protocol_name):
    global PROTOCOLS
    if protocol_name not in PROTOCOLS:
        PROTOCOLS[protocol_name] = load_auth_protocol(protocol_name)
    return PROTOCOLS[protocol_name]


class Federated(auth.AuthMethodHandler):
 
    def __init__(self):
        self.discovery_driver = importutils.import_object(CONF.auth.get("discovery"))
        self.mapping_api = importutils.import_object(CONF.auth.get("attribute_mapper"))
        self.issuing_policy = importutils.import_object(CONF.auth.get("issuing_policy"))

    def authenticate(self, context, auth_payload, auth_context):
        ''' Authenticate the user, auth_payload should contain:
            protocol - the protocol the identity provider uses
            provider_id - an identifier for the identity provider
            negotiation (Optional) - an intermediate communication
            assertion - an authentication assertion to be validated '''
        # Grab the phase parameter
        phase = auth_payload.get("phase", None)
        if not phase:
            return "Federated Requests must specify which stage of authentication has been reached"
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
            auth_context["user_id"] = user_management.UserManager().manage(response["uid"])
            for attribute_set in response["user_identity"]:
                validated = self.issuing_policy.check_issuers(attribute_set["attributes"],
                                                              attribute_set["provider"])
                for v in validated:
                    valid_attributes.update(v)
            auth_context["attributes"] = self.mapping_api.map(valid_attributes)
            auth_context["extras"]["projects"] = []
            for att in auth_context["attributes"]:
                for role in att["role"]:
                    for project in att["project"]:
                        auth_context["extras"]["projects"].append(self.assignment_api.get_project(project));
                        self.assignment_api.create_grant(role,
                                                       auth_context["user_id"],
                                                       project_id=project)
        return

    def discovery(self, auth_payload):
        ''' Return a list of available Identity Providers'''
        return {"response": self.discovery_driver.get_directory()}

    def request(self, auth_payload):
        ''' Create an authentication request for the provider in the auth payload.
        If a provider is not specified the return error message '''

        if not auth_payload.get("provider_id", None):
            raise exception.NotFound("Missing Provider ID")
        self.discovery_driver.populate_auth_dict(auth_payload,
                                                 auth_payload.get("provider_id"))
        protocol = auth_payload.get("protocol", None)
        response = get_auth_protocol(protocol).request_auth(auth_payload)
        return {"response": response}


    def validate(self, auth_payload):
        ''' Validate the response in a protocol appropriate manner
            and return the user ID, attributes and the validity of
            the validated response'''
        if not auth_payload.get("provider_id"):
            raise exception.NotFound("Missing Provider ID")
        resp = {"response": None}
        self.discovery_driver.populate_auth_dict(auth_payload,
                                                 auth_payload.get("provider_id"))
        if not auth_payload.get("protocol"):
            return {"response":"Protocol not found or not recognised"}

        resp['uid'], resp['user_identity'], resp['validity_time'] = get_auth_protocol(auth_payload["protocol"]).validate(auth_payload)
        return resp
