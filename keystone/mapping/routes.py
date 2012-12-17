# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC
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

from keystone.common import wsgi
import controllers


class MappingExtension(wsgi.ExtensionRouter):

    """

    Provides a bunch of CRUD operations for internal data types.

    """
    def add_routes(self, mapper):
        org_mapping_controller = controllers.OrgMappingController()
        os_mapping_controller = controllers.OsMappingController()
        mapping_controller = controllers.AttributeMappingController()

        # Attribute mapping operations
        # Org Sets
        mapper.connect('/mappings/orgattributeset',
                       controller=org_mapping_controller,
                       action='get_org_sets',
                       conditions=dict(method=['GET']))
        mapper.connect('/mappings/orgattributeset/{set_id}',
                       controller=org_mapping_controller,
                       action='get_org_sets',
                       conditions=dict(method=['GET']))
        mapper.connect('/mappings/orgattributeset/{set_id}',
                       controller=org_mapping_controller,
                       action='delete_org_set',
                       conditions=dict(method=['DELETE']))
        mapper.connect('/mappings/orgattributeset',
                       controller=org_mapping_controller,
                       action='create_org_set',
                       conditions=dict(method=['POST']))

        # Org Attributes
        mapper.connect('/mappings/orgattributes',
                       controller=org_mapping_controller,
                       action='get_org_atts',
                       conditions=dict(method=['GET']))
        mapper.connect('/mappings/orgattributes/{attribute_id}',
                       controller=org_mapping_controller,
                       action='get_org_atts',
                       conditions=dict(method=['GET']))
        mapper.connect('/mappings/orgattributes/{attribute_id}',
                       controller=org_mapping_controller,
                       action='delete_org_att',
                       conditions=dict(method=['DELETE']))
        mapper.connect('/mappings/orgattributes',
                       controller=org_mapping_controller,
                       action='create_org_att',
                       conditions=dict(method=['POST']))

        # Org Associations
        mapper.connect('/mappings/org/associations',
                       controller=org_mapping_controller,
                       action='get_org_assocs',
                       conditions=dict(method=['GET']))
        mapper.connect('/mappings/org/associations/{assoc_id}',
                       controller=org_mapping_controller,
                       action='get_org_assocs',
                       conditions=dict(method=['GET']))
        mapper.connect('/mappings/org/associations/{assoc_id}',
                       controller=org_mapping_controller,
                       action='delete_org_assoc',
                       conditions=dict(method=['DELETE']))
        mapper.connect('/mappings/orgattributeset',
                       controller=org_mapping_controller,
                       action='create_org_assoc',
                       conditions=dict(method=['POST']))

        # os Sets
        mapper.connect('/mappings/osattributeset',
                       controller=os_mapping_controller,
                       action='get_os_sets',
                       conditions=dict(method=['GET']))
        mapper.connect('/mappings/osattributeset/{set_id}',
                       controller=os_mapping_controller,
                       action='get_os_sets',
                       conditions=dict(method=['GET']))
        mapper.connect('/mappings/osattributeset/{set_id}',
                       controller=os_mapping_controller,
                       action='delete_os_set',
                       conditions=dict(method=['DELETE']))
        mapper.connect('/mappings/osattributeset',
                       controller=os_mapping_controller,
                       action='create_os_set',
                       conditions=dict(method=['POST']))

        # os Associations
        mapper.connect('/mappings/osattributeset/associations',
                       controller=os_mapping_controller,
                       action='get_os_assocs',
                       conditions=dict(method=['GET']))
        mapper.connect('/mappings/osattributeset/associations/{assoc_id}',
                       controller=os_mapping_controller,
                       action='get_os_assocs',
                       conditions=dict(method=['GET']))
        mapper.connect('/mappings/osattributeset/associations/{assoc_id}',
                       controller=os_mapping_controller,
                       action='delete_os_assoc',
                       conditions=dict(method=['DELETE']))
        mapper.connect('/mappings/osattributeset',
                       controller=os_mapping_controller,
                       action='create_os_assoc',
                       conditions=dict(method=['POST']))

        mapper.connect('/mappings',
                       controller=mapping_controller,
                       action='get_mappings',
                       conditions=dict(method=['GET']))
        mapper.connect('/mappings/{mapping_id}',
                       controller=mapping_controller,
                       action='get_mappings',
                       conditions=dict(method=['GET']))
        mapper.connect('/mappings/{mapping_id}',
                       controller=mapping_controller,
                       action='delete_mapping',
                       conditions=dict(method=['DELETE']))
        mapper.connect('/mappings',
                       controller=mapping_controller,
                       action='create_mapping',
                       conditions=dict(method=['POST']))

        mapper.connect('/mappings/map',
                       controller=mapping_controller,
                       action='get_mappings_from_attributes',
                       conditions=dict(method=['POST']))
