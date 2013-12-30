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
        mapping_file = CONF.auth.get("mapping_file")
        self.mapping_tree = ElementTree.parse(mapping_file)

    def map(self, attributes):
        valid_mappings = []
        # Call the mapping back end
        map_root = self.mapping_tree.getroot()
        for mapping in map_root.findall("AttributeMapping"):
            match = True
            external = mapping.find("ExternalAttributes")
            for attribute in external.findall("Attribute"):
                attribute_type = attribute.get("type")
                requirement = attribute.get("requirement")
                if requirement == "any":
                    if attribute_type in attributes.keys():
                        pass
                    else:
                        match = False
                else:
                    # Get the values for this attribute
                    values = []
                    for value in attribute.findall("AttributeValue"):
                        values.append(value.text)
                    if requirement == "one":
                        if attribute_type in attributes.keys():
                            # Check if one of the values is present
                            found = False
                            user_values = attributes.get(attribute_type)
                            for val in values:
                                if val in user_values:
                                    found = True
                            if not found:
                                match = False
                    if requirement == "all":
                        if attribute_type in attributes.keys():
                            # Check if one of the values is present
                            found = True
                            user_values = attributes.get(attribute_type)
                            for val in values:
                                if val not in user_values:
                                    found = False
                            if not found:
                                match = False
                    if requirement == "not":
                        if attribute_type in attributes.keys():
                            # Check if one of the values is present
                            found = False
                            user_values = attributes.get(attribute_type)
                            for val in values:
                                if val in user_values:
                                    found = True
                            if found:
                                match = False
                        else:
                            match = True
            if match:
                valid_mappings.append(self.tree_to_dict(mapping))
        return valid_mappings

    def tree_to_dict(self, mapping):
        attribute_dict = {}
        attributes = mapping.find("InternalAttributes").findall("Attribute")
        for attribute in attributes:
            attribute_type = attribute.get("type")
            values = [val.text for val in attribute.findall("AttributeValue")]
            if attribute_dict.get(attribute_type):
                for value in values:
                    attribute_dict[attribute_type].append(value)
            else:
                attribute_dict[attribute_type] = values
        return attribute_dict
