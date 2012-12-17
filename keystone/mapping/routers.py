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

from keystone.common import router
import controllers


def append_v3_routers(mapper, routers):

    routers.append(
        router.Router(controllers.OrgMappingController(),
                      'org_attributes', 'org_attribute'))
    routers.append(
        router.Router(controllers.OrgMappingController(),
                      'org_attribute_sets', 'org_attribute_set'))
    routers.append(
        router.Router(controllers.OsMappingController(),
                      'os_attribute_sets', 'os_attribute_set'))
    routers.append(
        router.Router(controllers.AttributeSetMappingController(),
                      'attribute_set_mappings', 'attribute_set_mapping'))

    mapper.connect('/os_attribute_sets/{os_attribute_set_id}/attributes',
                   controller=controllers.OsMappingController(),
                   action='list_attributes_in_os_set',
                   conditions=dict(method=['GET']))
    mapper.connect('/os_attribute_sets/{os_attribute_set_id}/'
                   + 'attributes/{attribute_id}',
                   controller=controllers.OsMappingController(),
                   action='add_attribute_to_os_set',
                   conditions=dict(method=['PUT']))
    mapper.connect('/os_attribute_sets/{os_attribute_set_id}/'
                   + 'attributes/{attribute_id}',
                   controller=controllers.OsMappingController(),
                   action='remove_attribute_from_os_set',
                   conditions=dict(method=['DELETE']))
    mapper.connect('/os_attribute_sets/{os_attribute_set_id}/'
                   + 'attributes/{attribute_id}',
                   controller=controllers.OsMappingController(),
                   action='check_attribute_in_os_set',
                   conditions=dict(method=['HEAD']))
    mapper.connect('/org_attribute_sets/{org_attribute_set_id}/attributes',
                   controller=controllers.OrgMappingController(),
                   action='list_attributes_in_org_set',
                   conditions=dict(method=['GET']))
    mapper.connect('/org_attribute_sets/{org_attribute_set_id}/'
                   + 'attributes/{attribute_id}',
                   controller=controllers.OrgMappingController(),
                   action='add_attribute_to_org_set',
                   conditions=dict(method=['PUT']))
    mapper.connect('/org_attribute_sets/{org_attribute_set_id}/'
                   + 'attributes/{attribute_id}',
                   controller=controllers.OrgMappingController(),
                   action='check_attribute_in_org_set',
                   conditions=dict(method=['HEAD']))
    mapper.connect('/org_attribute_sets/{org_attribute_set_id}/'
                   + 'attributes/{attribute_id}',
                   controller=controllers.OrgMappingController(),
                   action='remove_attribute_from_org_set',
                   conditions=dict(method=['DELETE']))
