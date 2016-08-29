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

import uuid

from keystone.tests import unit

class TestFederationProtocol(unit.TestCase):

    def setUp(self):
        super(TestFederationProtocol, self).setUp()
        self.useFixture(database.Database())
        self.load_backends()
        idp = {
            'id': id or uuid.uuid4().hex,
            'enabled': True,
            'description': uuid.uuid4().hex
        }
        self.federation_api.create_idp(self.idp['id'], self.idp)

    def test_create_protocol(self):
        mapping = {
            'id': uuid.uuid4().hex,
            'rules': None
        }
        self.federation_api.create_mapping(self.mapping['id'],
                                           self.mapping)
        protocol = {
            'id': uuid.uuid4().hex,
            'mapping_id': mapping['id']
        }
        self.federation_api.create_protocol(self.idp['id'],
                                            protocol['id'],
                                            protocol)
        # create protocol ref
        # api call to create protocol
    """
    def test_create_protocol_with_invalid_mapping(self):
    def test_update_protocol(self):
    def test_update_protocol_with_invalid_mapping(self):
    """
