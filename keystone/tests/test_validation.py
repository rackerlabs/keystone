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

from keystone.assignment import schema as assignment_schema
from keystone import exception
from keystone import tests
from keystone.validation import models
from keystone.validation import parameter_types


# Test schema to validate create requests against
class SimpleCreate(models.Request):

    schema = {
        'type': 'object',
        'properties': {
            'name': parameter_types.name,
            'description': parameter_types.description,
            'enabled': parameter_types.boolean
        },
        'required': ['name'],
        'additionalProperties': True,
    }


class SimpleUpdate(models.Request):
    pass


_VALID_ENABLED_FORMATS = [True, 'True', 'TRUE', 'true', '1',
                          False, 'False', 'FALSE', 'false', '0']

_INVALID_ENABLED_FORMATS = ['some string', 1, 0]


class BaseValidationTestCase(tests.TestCase):

    Create = SimpleCreate
    Update = SimpleUpdate

    def setUp(self):
        super(BaseValidationTestCase, self).setUp()
        self.resource_name = 'some resource name'
        self.description = 'Some valid description'
        self.valid_enabled = True

    def test_create_schema_with_all_valid_parameters(self):
        """Test that we can validate a request with proper parameters."""
        request_to_validate = {'name': self.resource_name,
                               'some_uuid': uuid.uuid4().hex,
                               'description': self.description,
                               'enabled': self.valid_enabled}
        self.Create(request_to_validate).validate()

    def test_create_schema_with_invalid_enabled_format_raises_exception(self):
        """Test that we raise an exception when `enabled` isn't a valid
           boolean value.
        """
        invalid_enabled_formats = 'some string'
        request_to_validate = {'name': self.resource_name,
                               'enabled': invalid_enabled_formats}

        create = self.Create(request_to_validate)
        self.assertRaises(exception.SchemaValidationError,
                          create.validate)

    def test_create_schema_with_valid_enabled_formats(self):
        """Test that we can validate `enabled` as boolean-like values."""
        for valid_enabled in _VALID_ENABLED_FORMATS:
            request_to_validate = {'name': self.resource_name,
                                   'enabled': valid_enabled}
            # Make sure validation doesn't raise a validation exception
            self.Create(request_to_validate).validate()


class ProjectValidationTestCase(BaseValidationTestCase):
    """Test for V3 Project API validation."""

    Create = assignment_schema.ProjectCreate
    Update = assignment_schema.ProjectUpdate
    Delete = assignment_schema.ProjectDelete

    def setUp(self):
        super(ProjectValidationTestCase, self).setUp()

        self.project_name = 'My Project'

    def test_validate_project_request(self):
        """Test that we validate a project with `name` in request."""
        request_to_validate = {'name': self.project_name}

        self.Create(request_to_validate).validate()

    def test_validate_project_request_without_name_raises_exception(self):
        """Test that an exception is raised when `name` isn't in the project
           creation request.
        """
        request_to_validate = {'enabled': True}
        create = self.Create(request_to_validate)
        self.assertRaises(exception.SchemaValidationError, create.validate)

    def test_validate_project_request_with_enabled(self):
        """Test that we can validate `enabled` as boolean-like values for
           projects.
        """
        for valid_enabled in _VALID_ENABLED_FORMATS:
            request_to_validate = {'name': self.project_name,
                                   'enabled': valid_enabled}
            self.Create(request_to_validate).validate()

    def test_validate_project_request_with_invalid_enabled_fails(self):
        """Test that an exception is raised when `enabled` isn't a
           boolean-like value.
        """
        for invalid_enabled in _INVALID_ENABLED_FORMATS:
            request_to_validate = {'name': self.project_name,
                                   'enabled': invalid_enabled}
            create = self.Create(request_to_validate)
            self.assertRaises(exception.SchemaValidationError, create.validate)

    def test_validate_project_request_with_valid_description(self):
        """Test that we validate `description` in create project requests."""
        request_to_validate = {'name': self.project_name,
                               'description': 'My Project'}
        self.Create(request_to_validate).validate()

    def test_validate_project_request_with_invalid_description(self):
        """Test that an exception is raised when validating `description` as a
           non-string value.
        """
        request_to_validate = {'name': self.project_name,
                               'description': False}
        create = self.Create(request_to_validate)
        self.assertRaises(exception.SchemaValidationError, create.validate)

    def test_validate_project_update_request(self):
        """Test that we validate a project update request."""
        request_to_validate = {'domain_id': uuid.uuid4().hex}
        self.Update(request_to_validate).validate()

    def test_validate_project_update_request_with_no_parameters_fails(self):
        """Test that an exception is raised when updating a project without
           any parameters.
        """
        request_to_validate = {}
        update = self.Update(request_to_validate)
        self.assertRaises(exception.SchemaValidationError, update.validate)

    def test_validate_project_delete_request_takes_no_parameters(self):
        """Test the delete validation schema."""
        request_to_validate = {}
        self.Delete(request_to_validate).validate()

    def test_validate_project_delete_with_parameters_raises_exception(self):
        """Test that an exception is raised when validating a delete request
           that has parameters.
        """
        request_to_validate = {'enabled': True}
        delete = self.Delete(request_to_validate)
        self.assertRaises(exception.SchemaValidationError, delete.validate)


class DomainValidationTestCase(BaseValidationTestCase):
    """Test for V3 Domain API validation."""

    Create = assignment_schema.DomainCreate
    Update = assignment_schema.DomainUpdate

    def setUp(self):
        super(DomainValidationTestCase, self).setUp()

        self.domain_name = 'My Domain'

    def test_validate_domain_request(self):
        """Make sure we successfully validate a create domain request."""
        request_to_validate = {'name': self.domain_name}
        self.Create(request_to_validate).validate()

    def test_validate_domain_request_without_name_raises_exception(self):
        """Make sure we raise an exception when `name` isn't included."""
        request_to_validate = {'enabled': True}
        create = self.Create(request_to_validate)
        self.assertRaises(exception.SchemaValidationError, create.validate)

    def test_validate_domain_request_with_enabled(self):
        """Test that we can validate `enabled` as boolean-like values for
           domains.
        """
        for valid_enabled in _VALID_ENABLED_FORMATS:
            request_to_validate = {'name': self.domain_name,
                                   'enabled': valid_enabled}
            # Make sure an exception isn't raised
            self.Create(request_to_validate).validate()

    def test_validate_domain_request_with_invalid_enabled_fails(self):
        """Test that an exception is raised when `enabled` isn't a
           boolean-like value.
        """
        for invalid_enabled in _INVALID_ENABLED_FORMATS:
            request_to_validate = {'name': self.domain_name,
                                   'enabled': invalid_enabled}
            create = self.Create(request_to_validate)
            self.assertRaises(exception.SchemaValidationError, create.validate)

    def test_validate_domain_request_with_valid_description(self):
        """Test that we validate `description` in create domain requests."""
        request_to_validate = {'name': self.domain_name,
                               'description': 'My Domain'}
        self.Create(request_to_validate).validate()

    def test_validate_domain_request_with_invalid_description(self):
        """Test that an exception is raised when validating `description` as a
           non-string value.
        """
        request_to_validate = {'name': self.domain_name,
                               'description': False}
        create = self.Create(request_to_validate)
        self.assertRaises(exception.SchemaValidationError, create.validate)

    def test_validate_domain_update_request(self):
        """Test that we validate a domain update request."""
        request_to_validate = {'domain_id': uuid.uuid4().hex}
        self.Update(request_to_validate).validate()

    def test_validate_domain_update_request_with_no_parameters_fails(self):
        """Test that an exception is raised when updating a domain without
           any parameters.
        """
        request_to_validate = {}
        update = self.Update(request_to_validate)
        self.assertRaises(exception.SchemaValidationError, update.validate)


class RoleValidationTestCase(BaseValidationTestCase):
    """Test for V3 Role API validation."""

    Create = assignment_schema.RoleCreate
    Update = assignment_schema.RoleUpdate

    def setUp(self):
        super(RoleValidationTestCase, self).setUp()

        self.role_name = 'My Role'

    def test_validate_role_request(self):
        """Test we can successfully validate a create role request."""
        request_to_validate = {'name': self.role_name}
        self.Create(request_to_validate).validate()

    def test_validate_role_create_without_name_raises_exception(self):
        """Test that we raise an exception when `name` isn't included."""
        request_to_validate = {'enabled': True}
        create = self.Create(request_to_validate)
        self.assertRaises(exception.SchemaValidationError, create.validate)

    def test_validate_role_create_when_name_is_not_string_fails(self):
        """Test that an exception is raised when creating a role with a `name`
           that isn't a string.
        """
        request_to_validate = {'name': True}
        create = self.Create(request_to_validate)
        self.assertRaises(exception.SchemaValidationError, create.validate)
        request_to_validate = {'name': 24}
        create = self.Create(request_to_validate)
        self.assertRaises(exception.SchemaValidationError, create.validate)

    def test_validate_role_update_request(self):
        """Test that we validate a role update request."""
        request_to_validate = {'name': 'My New Role'}
        self.Update(request_to_validate).validate()

    def test_validate_role_update_fails_with_invalid_name(self):
        """Test that we raise an exception when validating an update request
           with an invalid `name`.
        """
        request_to_validate = {'name': True}
        update = self.Update(request_to_validate)
        self.assertRaises(exception.SchemaValidationError, update.validate)

        request_to_validate = {'name': 24}
        update = self.Update(request_to_validate)
        self.assertRaises(exception.SchemaValidationError, update.validate)
