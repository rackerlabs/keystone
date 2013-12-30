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

from keystone.common import config

from xml.etree import ElementTree

CONF = config.CONF


class Default(object):

    def __init__(self):
        issuing_policy_file = CONF.auth.get("issuing_policy_file")
        self.policy_tree = ElementTree.parse(issuing_policy_file)

    def check_issuers(self, attributes, provider):
        '''Check whether the given provider can issue the given set of
           attributes, Remove all invalid attributes before returning
           the filtered list
        '''
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
