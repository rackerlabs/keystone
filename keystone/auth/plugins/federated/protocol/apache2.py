'''
Created on 20 Dec 2013

@author: kwss

Passes authentication information from Apache2
to the core federated module for trust management

'''
import core

from keystone import exception


class Apache2(core.ProtocolHandler):
    
    def validate(self, auth_payload):
        uid = auth_payload['protocol_data']["uid"]
        attributes = auth_payload['protocol_data']["user_identity"]
        expiry = auth_payload['protocol_data']["validity_time"]
	return uid, attributes, expiry
    
    def request_auth(self, auth_payload):
        raise exception.NotImplemented()
