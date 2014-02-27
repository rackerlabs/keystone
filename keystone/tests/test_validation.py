# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import uuid


from keystone import tests
from keystone import validation
from keystone.validation import common_parameter_types

# Test schema to validate create requests against
CREATE = {
    'type': 'object',
    'properties': {
        'name': common_parameter_types.name,
        'some_uuid': common_parameter_types.uuid,
        'description': {
            'type': 'string',
            'pattern': '^[a-zA-Z0-9-._ ]*$'
        },
        'enabled': common_parameter_types.boolean,
    },
    'required': ['name'],
    'additionalProperties': True,
}


UPDATE = {}


class ValidationTestCase(tests.TestCase):


    def test_create_schema_with_all_valid_parameters(self):
        valid_uuid = uuid.uuid4().hex
        description = ('Some valid description of the new resource we '
                       'are creating')
        request_to_validate = {'name': 'some resource name',
                               'some_uuid': valid_uuid,
                               'description': description,
                               'enabled': True}
        validation.schema(CREATE, request_to_validate)

    def test_create_schema_invalid_uuid(self):
        invalid_uuid = 'Some-invalid-idz'
        request_to_validate = {'name': 'some resource name',
                               'some_uuid': invalid_uuid}
        validation.schema(CREATE, request_to_validate)

