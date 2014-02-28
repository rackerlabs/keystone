# -*- coding: utf-8 -*-
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
from keystone.common.validation import parameter_types
from keystone.common.validation import validators
from keystone import exception
from keystone import tests


# Test schema to validate create requests against
_CREATE = {
    'type': 'object',
    'properties': {
        'name': parameter_types.name,
        'description': parameter_types.description,
        'enabled': parameter_types.boolean,
        'url': parameter_types.url,
        'email': parameter_types.email,
        'uuid': parameter_types.required_id_string,
        'user_id': parameter_types.optional_id_string
    },
    'required': ['name'],
    'additionalProperties': True,
}

_UPDATE = {}

_VALID_ENABLED_FORMATS = [True, False]

_INVALID_ENABLED_FORMATS = ['some string', 1, 0, 'True', 'False']


class BaseValidationTestCase(tests.TestCase):

    def setUp(self):
        super(BaseValidationTestCase, self).setUp()
        self.resource_name = 'some resource name'
        self.description = 'Some valid description'
        self.valid_enabled = True
        self.valid_url = 'http://example.com'
        self.valid_email = 'joe@example.com'
        self.config_fixture.config(group='validation',
                                   id_string_regex='^[a-zA-Z0-9-]+$')
        self.create_schema_validator = validators.SchemaValidator(_CREATE)
        self.update_schema_validator = validators.SchemaValidator(_UPDATE)

    def test_create_schema_with_all_valid_parameters(self):
        """Validate proper values against test schema."""
        request_to_validate = {'name': self.resource_name,
                               'some_uuid': uuid.uuid4().hex,
                               'description': self.description,
                               'enabled': self.valid_enabled,
                               'url': self.valid_url}
        self.create_schema_validator.validate(request_to_validate)

    def test_create_schema_with_name_too_long_raises_exception(self):
        """Validate long names.

        Validate that an exception is raised when validating a string of 255+
        characters passed in as a name.
        """
        invalid_name = ''
        for i in range(255):
            invalid_name = invalid_name + str(i)

        request_to_validate = {'name': invalid_name}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_schema_validator.validate,
                          request_to_validate)

    def test_create_schema_with_name_too_short_raises_exception(self):
        """Validate short names.

        Test that an exception is raised when passing a string of length
        zero as a name parameter.
        """
        request_to_validate = {'name': ''}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_schema_validator.validate,
                          request_to_validate)

    def test_create_schema_with_unicode_name_is_successful(self):
        """Test that we successfully validate a unicode string."""
        request_to_validate = {'name': u'αβγδ'}
        self.create_schema_validator.validate(request_to_validate)

    def test_create_schema_with_invalid_enabled_format_raises_exception(self):
        """Validate invalid enabled formats.

        Test that an exception is raised when passing invalid boolean-like
        values as `enabled`.
        """
        invalid_enabled_formats = 'some string'
        request_to_validate = {'name': self.resource_name,
                               'enabled': invalid_enabled_formats}

        self.assertRaises(exception.SchemaValidationError,
                          self.create_schema_validator.validate,
                          request_to_validate)

    def test_create_schema_with_valid_enabled_formats(self):
        """Validate valid enabled formats.

        Test that we have successful validation on boolean values for
        `enabled`.
        """
        valid_enabled_formats = [True, False]

        for valid_enabled in valid_enabled_formats:
            request_to_validate = {'name': self.resource_name,
                                   'enabled': valid_enabled}
            # Make sure validation doesn't raise a validation exception
            self.create_schema_validator.validate(request_to_validate)

    def test_create_schema_with_valid_urls(self):
        """Test that proper urls are successfully validated."""
        valid_urls = ['https://169.254.0.1', 'https://example.com',
                      'https://EXAMPLE.com', 'https://127.0.0.1:35357',
                      'https://localhost']

        for valid_url in valid_urls:
            request_to_validate = {'name': self.resource_name,
                                   'url': valid_url}
            self.create_schema_validator.validate(request_to_validate)

    def test_create_schema_with_invalid_urls(self):
        """Test that an exception is raised when validating improper urls."""
        invalid_urls = ['http//something.com',
                        'https//something.com',
                        'https://9.9.9']

        for invalid_url in invalid_urls:
            request_to_validate = {'name': self.resource_name,
                                   'url': invalid_url}
            self.assertRaises(exception.SchemaValidationError,
                              self.create_schema_validator.validate,
                              request_to_validate)

    def test_create_schema_with_valid_email(self):
        """Validate email address

        Test that we successfully validate properly formatted email
        addresses.
        """
        request_to_validate = {'name': self.resource_name,
                               'email': self.valid_email}
        self.create_schema_validator.validate(request_to_validate)

    def test_create_schema_with_invalid_email(self):
        """Validate invalid email address

        Test that an exception is raised when validating improperly
        formatted email addresses.
        """
        request_to_validate = {'name': self.resource_name,
                               'email': 'some invalid email value'}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_schema_validator.validate,
                          request_to_validate)

    def test_create_schema_with_valid_id_strings(self):
        """Validate acceptable id strings."""
        valid_id_strings = ['699d5241-1233-4876-a9fa-427960cc9cd3',
                            '0b7ed71f308e4d31bbf9c82496420ef7',
                            'default']
        for valid_id in valid_id_strings:
            request_to_validate = {'name': self.resource_name,
                                   'uuid': valid_id}
            self.create_schema_validator.validate(request_to_validate)

    def test_create_schema_with_invalid_id_strings(self):
        """Exception raised when using invalid id strings."""
        long_string = "A" * 65
        invalid_id_strings = ['',
                              long_string,
                              'this,should,fail']
        for invalid_id in invalid_id_strings:
            request_to_validate = {'name': self.resource_name,
                                   'uuid': invalid_id}
            self.assertRaises(exception.SchemaValidationError,
                              self.create_schema_validator.validate,
                              request_to_validate)

    def test_create_schema_with_null_string_id(self):
        """Validate that None is an acceptable optional string type."""
        request_to_validate = {'name': self.resource_name,
                               'user_id': None}
        self.create_schema_validator.validate(request_to_validate)

    def test_create_schema_with_null_string_on_required_fails(self):
        """Exception raised when passing None on required id strings."""
        request_to_validate = {'name': self.resource_name,
                               'uuid': None}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_schema_validator.validate,


class ProjectValidationTestCase(BaseValidationTestCase):
    """Test for V3 Project API validation."""

    def setUp(self):
        super(ProjectValidationTestCase, self).setUp()

        self.project_name = 'My Project'

        create = assignment_schema.project_create
        update = assignment_schema.project_update
        delete = assignment_schema.project_delete
        self.create_project_validator = validators.SchemaValidator(create)
        self.update_project_validator = validators.SchemaValidator(update)
        self.delete_project_validator = validators.SchemaValidator(delete)

    def test_validate_project_request(self):
        """Test that we validate a project with `name` in request."""
        request_to_validate = {'name': self.project_name}
        self.create_project_validator.validate(request_to_validate)

    def test_validate_project_request_without_name_fails(self):
        """Validate project request fails without name."""
        request_to_validate = {'enabled': True}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_project_validator.validate,
                          request_to_validate)

    def test_validate_project_request_with_enabled(self):
        """Validate `enabled` as boolean-like values for projects."""
        for valid_enabled in _VALID_ENABLED_FORMATS:
            request_to_validate = {'name': self.project_name,
                                   'enabled': valid_enabled}
            self.create_project_validator.validate(request_to_validate)

    def test_validate_project_request_with_invalid_enabled_fails(self):
        """Exception is raised when `enabled` isn't a boolean-like value."""
        for invalid_enabled in _INVALID_ENABLED_FORMATS:
            request_to_validate = {'name': self.project_name,
                                   'enabled': invalid_enabled}
            self.assertRaises(exception.SchemaValidationError,
                              self.create_project_validator.validate,
                              request_to_validate)

    def test_validate_project_request_with_valid_description(self):
        """Test that we validate `description` in create project requests."""
        request_to_validate = {'name': self.project_name,
                               'description': 'My Project'}
        self.create_project_validator.validate(request_to_validate)

    def test_validate_project_request_with_invalid_description_fails(self):
        """Exception is raised when `description` as a non-string value."""
        request_to_validate = {'name': self.project_name,
                               'description': False}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_project_validator.validate,
                          request_to_validate)

    def test_validate_project_update_request(self):
        """Test that we validate a project update request."""
        request_to_validate = {'domain_id': uuid.uuid4().hex}
        self.update_schema_validator.validate(request_to_validate)

    def test_validate_project_update_request_with_no_parameters_fails(self):
        """Exception is raised when updating project without parameters."""
        request_to_validate = {}
        self.assertRaises(exception.SchemaValidationError,
                          self.update_project_validator.validate,
                          request_to_validate)

    def test_validate_project_delete_request_takes_no_parameters(self):
        """Test the delete validation schema."""
        request_to_validate = {}
        self.delete_project_validator.validate(request_to_validate)

    def test_validate_project_delete_with_parameters_fails(self):
        """Exception is raised on validate delete request with parameters."""
        request_to_validate = {'enabled': True}
        self.assertRaises(exception.SchemaValidationError,
                          self.delete_project_validator.validate,
                          request_to_validate)


class DomainValidationTestCase(BaseValidationTestCase):
    """Test for V3 Domain API validation."""

    def setUp(self):
        super(DomainValidationTestCase, self).setUp()

        self.domain_name = 'My Domain'

        create = assignment_schema.domain_create
        update = assignment_schema.domain_update
        self.create_domain_validator = validators.SchemaValidator(create)
        self.update_domain_validator = validators.SchemaValidator(update)

    def test_validate_domain_request(self):
        """Make sure we successfully validate a create domain request."""
        request_to_validate = {'name': self.domain_name}
        self.create_domain_validator.validate(request_to_validate)

    def test_validate_domain_request_without_name_fails(self):
        """Make sure we raise an exception when `name` isn't included."""
        request_to_validate = {'enabled': True}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_domain_validator.validate,
                          request_to_validate)

    def test_validate_domain_request_with_enabled(self):
        """Validate `enabled` as boolean-like values for domains."""
        for valid_enabled in _VALID_ENABLED_FORMATS:
            request_to_validate = {'name': self.domain_name,
                                   'enabled': valid_enabled}
            self.create_domain_validator.validate(request_to_validate)

    def test_validate_domain_request_with_invalid_enabled_fails(self):
        """Exception is raised when `enabled` isn't a boolean-like value."""
        for invalid_enabled in _INVALID_ENABLED_FORMATS:
            request_to_validate = {'name': self.domain_name,
                                   'enabled': invalid_enabled}
            self.assertRaises(exception.SchemaValidationError,
                              self.create_domain_validator.validate,
                              request_to_validate)

    def test_validate_domain_request_with_valid_description(self):
        """Test that we validate `description` in create domain requests."""
        request_to_validate = {'name': self.domain_name,
                               'description': 'My Domain'}
        self.create_domain_validator.validate(request_to_validate)

    def test_validate_domain_request_with_invalid_description_fails(self):
        """Exception is raised when `description` is a non-string value."""
        request_to_validate = {'name': self.domain_name,
                               'description': False}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_domain_validator.validate,
                          request_to_validate)

    def test_validate_domain_update_request(self):
        """Test that we validate a domain update request."""
        request_to_validate = {'domain_id': uuid.uuid4().hex}
        self.update_schema_validator.validate(request_to_validate)

    def test_validate_domain_update_request_with_no_parameters_fails(self):
        """Exception is raised when updating a domain without parameters."""
        request_to_validate = {}
        self.assertRaises(exception.SchemaValidationError,
                          self.update_domain_validator.validate,
                          request_to_validate)


class RoleValidationTestCase(BaseValidationTestCase):
    """Test for V3 Role API validation."""

    def setUp(self):
        super(RoleValidationTestCase, self).setUp()

        self.role_name = 'My Role'

        create = assignment_schema.role_create
        update = assignment_schema.role_update
        self.create_role_validator = validators.SchemaValidator(create)
        self.update_role_validator = validators.SchemaValidator(update)

    def test_validate_role_request(self):
        """Test we can successfully validate a create role request."""
        request_to_validate = {'name': self.role_name}
        self.create_role_validator.validate(request_to_validate)

    def test_validate_role_create_without_name_raises_exception(self):
        """Test that we raise an exception when `name` isn't included."""
        request_to_validate = {'enabled': True}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_role_validator.validate,
                          request_to_validate)

    def test_validate_role_create_when_name_is_not_string_fails(self):
        """Exception is raised on role create with a non-string `name`."""
        request_to_validate = {'name': True}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_role_validator.validate,
                          request_to_validate)
        request_to_validate = {'name': 24}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_role_validator.validate,
                          request_to_validate)

    def test_validate_role_update_request(self):
        """Test that we validate a role update request."""
        request_to_validate = {'name': 'My New Role'}
        self.update_role_validator.validate(request_to_validate)

    def test_validate_role_update_fails_with_invalid_name_fails(self):
        """Exception when validating an update request with invalid `name`."""
        request_to_validate = {'name': True}
        self.assertRaises(exception.SchemaValidationError,
                          self.update_role_validator.validate,
                          request_to_validate)

        request_to_validate = {'name': 24}
        self.assertRaises(exception.SchemaValidationError,
                          self.update_role_validator.validate,
                          request_to_validate)
