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

"""Extensions supporting Assertion Mapping."""

from keystone.common import controller
from keystone.common import dependency
from keystone import config
from keystone.contrib.mapping import core


CONF = config.CONF


@dependency.requires('mapping_api')
class MappingController(controller.V3Controller):
    collection_name = 'mappings'
    member_name = 'mapping'

    @controller.protected()
    def create_mapping(self, context, mapping):
        ref = self._assign_unique_id(self._normalize_dict(mapping))
        core.validate_mapping_structure(ref)
        mapping_ref = self.mapping_api.create_mapping(ref)
        return MappingController.wrap_member(context, mapping_ref)

    @controller.protected()
    def list_mappings(self, context):
        ref = self.mapping_api.list_mappings()
        return MappingController.wrap_collection(context, ref)

    @controller.protected()
    def get_mapping(self, context, mapping_id):
        ref = self.mapping_api.get_mapping(mapping_id)
        return MappingController.wrap_member(context, ref)

    @controller.protected()
    def delete_mapping(self, context, mapping_id):
        self.mapping_api.delete_mapping(mapping_id)

    @controller.protected()
    def update_mapping(self, context, mapping_id, mapping):
        mapping = self._normalize_dict(mapping)
        core.validate_mapping_structure(mapping)
        mapping_ref = self.mapping_api.update_mapping(mapping_id, mapping)
        return MappingController.wrap_member(context, mapping_ref)
