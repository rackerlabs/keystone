'''
Created on 5 Jun 2013

@author: kwss
'''
from xml.etree import ElementTree
from keystone.common import config


CONF = config.CONF

class Default(object):
    def __init__(self):
        issuing_policy_file = CONF.auth.get("issuing_policy_file")
        self.policy_tree = ElementTree.parse(issuing_policy_file) 
       
    def check_issuers(self, attributes, provider):
        ''' Check whether the given provider can issue the given set of attributes,
            Remove all invalid attributes before returning the filtered list '''
        for issuer in self.policy_tree.getroot().findall("Issuer"):
            if issuer.get("service_id") == provider:
                atts = {}
                # Get the attributes which can be issued by this issuer
                for att in issuer.find("Attributes").findall("Attribute"):
                    atts[att.get("type")] = []
                    for val in att.findall("AttributeValue"):
                        atts[att.get("type")].append(val.text)
                invalid_attributes = []
                for attribute in attributes:                   
                    values = attributes[attribute]
                    vals = atts.get(attribute)
                    # Check if the attribute can be issued
                    if vals is None or len(vals) == 0:
                        invalid_attributes.append(attribute)
                    else:
                        valid_vals = []
                        for value in values:
                            if value in vals:
                                valid_vals.append(value)
                        if len(valid_vals) > 0:
                            attributes[attribute] = valid_vals
                # Remove all invalid attributes
                for invalid in invalid_attributes:
                    attributes.pop(invalid)
        return attributes    
