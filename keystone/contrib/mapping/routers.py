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

from keystone.common import wsgi
from keystone.contrib.mapping import controllers


class MappingExtension(wsgi.ExtensionRouter):
    """API Endpoints for the Mapping extension.

    The API looks like:
    #TODO(stevemar): Add API for mapping
    """

    def add_routes(self, mapper):
        mapping_controller = controllers.MappingController()

        mapper.connect(
            '/OS-MAP/mappings',
            controller=mapping_controller,
            action='create_mapping',
            conditions=dict(method=['POST']))

        mapper.connect(
            '/OS-MAP/mappings',
            controller=mapping_controller,
            action='list_mappings',
            conditions=dict(method=['GET']))

        mapper.connect(
            '/OS-MAP/mappings/{mapping_id}',
            controller=mapping_controller,
            action='get_mapping',
            conditions=dict(method=['GET']))

        mapper.connect(
            '/OS-MAP/mappings/{mapping_id}',
            controller=mapping_controller,
            action='delete_mapping',
            conditions=dict(method=['DELETE']))

        mapper.connect(
            '/OS-MAP/mappings/{mapping_id}',
            controller=mapping_controller,
            action='update_mapping',
            conditions=dict(method=['PATCH']))
