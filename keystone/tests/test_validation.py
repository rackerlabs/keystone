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

from keystone.catalog import schema as catalog_schema
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
        'email': parameter_types.email
    },
    'required': ['name'],
    'additionalProperties': True,
}


class ValidationTestCase(tests.TestCase):

    def setUp(self):
        super(ValidationTestCase, self).setUp()
        self.resource_name = 'some resource name'
        self.description = 'Some valid description'
        self.valid_enabled = True
        self.valid_url = 'http://example.com'
        self.valid_email = 'joe@example.com'
        self.create_schema_validator = validators.SchemaValidator(_CREATE)

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


class RegionValidationTestCase(BaseValidationTestCase):
    """Test for V3 Region API validation."""

    def setUp(self):
        super(RegionValidationTestCase, self).setUp()

        self.region_name = 'My Region'

        create = catalog_schema.region_create
        update = catalog_schema.region_update
        self.create_region_validator = validators.SchemaValidator(create)
        self.update_region_validator = validators.SchemaValidator(update)

    def test_validate_region_request(self):
        """Test that we validate a basic region request."""
        # Create_region doesn't take any parameters in the request so let's
        # make sure we cover that case.
        request_to_validate = {}
        self.create_region_validator.validate(request_to_validate)

    def test_validate_region_create_request_with_parameters(self):
        """Test that we validate a region request with parameters."""
        request_to_validate = {'id': 'us-east',
                               'description': 'US East Region',
                               'parent_region_id': 'US Region'}
        self.create_region_validator.validate(request_to_validate)

    def test_validate_region_create_with_uuid(self):
        """Test that we validate a region request with a UUID as the id."""
        request_to_validate = {'id': uuid.uuid4().hex,
                               'description': 'US East Region',
                               'parent_region_id': uuid.uuid4().hex}
        self.create_region_validator.validate(request_to_validate)

    def test_validate_region_create_succeeds_with_extra_parameters(self):
        """Validate create region request with extra values."""
        request_to_validate = {'other_attr': uuid.uuid4().hex}
        self.create_region_validator.validate(request_to_validate)

    def test_validate_region_update_succeeds(self):
        """Test that we validate a region update request."""
        request_to_validate = {'id': 'us-west',
                               'description': 'US West Region',
                               'parent_region_id': 'us-region'}
        self.update_region_validator.validate(request_to_validate)

    def test_validate_region_update_succeeds_with_extra_parameters(self):
        """Validate extra attributes in the region update request."""
        request_to_validate = {'other_attr': uuid.uuid4().hex}
        self.update_region_validator.validate(request_to_validate)

    def test_validate_region_update_fails_with_no_parameters(self):
        """Exception raised when passing no parameters in a region update."""
        # An update request should consist of at least one value to update
        request_to_validate = {}
        self.assertRaises(exception.SchemaValidationError,
                          self.update_region_validator.validate,
                          request_to_validate)


class ServiceValidationTestCase(BaseValidationTestCase):
    """Test for V3 Service API validation."""

    def setUp(self):
        super(ServiceValidationTestCase, self).setUp()

        create = catalog_schema.service_create
        update = catalog_schema.service_update
        self.create_service_validator = validators.SchemaValidator(create)
        self.update_service_validator = validators.SchemaValidator(update)

    def test_validate_service_create_succeeds(self):
        """Test that we validate a service create request."""
        request_to_validate = {'name': 'Nova',
                               'description': 'OpenStack Compute Service',
                               'enabled': True,
                               'type': 'compute'}
        self.create_service_validator.validate(request_to_validate)

    def test_validate_service_create_succeeds_with_required_parameters(self):
        """Validate a service create request with the required parameters."""
        # The only parameter type required for service creation is 'type'
        request_to_validate = {'type': 'compute'}
        self.create_service_validator.validate(request_to_validate)

    def test_validate_service_create_fails_without_type(self):
        """Exception raised when trying to create a service without `type`."""
        request_to_validate = {'name': 'Nova'}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_service_validator.validate,
                          request_to_validate)

    def test_validate_service_create_succeeds_with_extra_parameters(self):
        """Test that extra parameters pass validation on create service."""
        request_to_validate = {'other_attr': uuid.uuid4().hex,
                               'type': uuid.uuid4().hex}
        self.create_service_validator.validate(request_to_validate)

    def test_validate_service_create_succeeds_with_valid_enabled(self):
        """Validate boolean values as `enabled`values on service create."""
        for valid_enabled in _VALID_ENABLED_FORMATS:
            request_to_validate = {'enabled': valid_enabled,
                                   'type': uuid.uuid4().hex}
            self.create_service_validator.validate(request_to_validate)

    def test_validate_service_create_fails_with_invalid_enabled(self):
        """Exception raised when boolean-like parameters as `enabled`

        On service create, make sure an exception is raised if `enabled` is
        not a boolean value.
        """
        for invalid_enabled in _INVALID_ENABLED_FORMATS:
            request_to_validate = {'enabled': invalid_enabled,
                                   'type': uuid.uuid4().hex}
            self.assertRaises(exception.SchemaValidationError,
                              self.create_service_validator.validate,
                              request_to_validate)

    def test_validate_service_update_request_succeeds(self):
        """Test that we validate a service update request."""
        request_to_validate = {'name': 'Cinder',
                               'type': 'volume',
                               'description': 'OpenStack Block Storage',
                               'enabled': False}
        self.update_service_validator.validate(request_to_validate)

    def test_validate_service_update_fails_with_no_parameters(self):
        """Exception raised when updating a service without values."""
        request_to_validate = {}
        self.assertRaises(exception.SchemaValidationError,
                          self.update_service_validator.validate,
                          request_to_validate)

    def test_validate_service_update_succeeds_with_extra_parameters(self):
        """Validateupdating a service with extra parameters."""
        request_to_validate = {'other_attr': uuid.uuid4().hex}
        self.update_service_validator.validate(request_to_validate)

    def test_validate_service_update_succeeds_with_valid_enabled(self):
        """Validate boolean formats as `enabled` on service update."""
        for valid_enabled in _VALID_ENABLED_FORMATS:
            request_to_validate = {'enabled': valid_enabled}
            self.update_service_validator.validate(request_to_validate)

    def test_validate_service_update_fails_with_invalid_enabled(self):
        """Exception raised when boolean-like values as `enabled`."""
        for invalid_enabled in _INVALID_ENABLED_FORMATS:
            request_to_validate = {'enabled': invalid_enabled}
            self.assertRaises(exception.SchemaValidationError,
                              self.update_service_validator.validate,
                              request_to_validate)


class EndpointValidationTestCase(BaseValidationTestCase):
    """Test for V3 Endpoint API validation."""

    def setUp(self):
        super(EndpointValidationTestCase, self).setUp()

        create = catalog_schema.endpoint_create
        update = catalog_schema.endpoint_update
        self.create_endpoint_validator = validators.SchemaValidator(create)
        self.update_endpoint_validator = validators.SchemaValidator(update)

    def test_validate_endpoint_request_succeeds(self):
        """Test that we validate an endpoint request."""
        request_to_validate = {'enabled': True,
                               'interface': 'admin',
                               'region_id': uuid.uuid4().hex,
                               'service_id': uuid.uuid4().hex,
                               'url': 'https://service.example.com:5000/'}
        self.create_endpoint_validator.validate(request_to_validate)

    def test_validate_endpoint_create_succeeds_with_required_parameters(self):
        """Validate an endpoint request with only the required parameters."""
        # According to the Identity V3 API endpoint creation requires
        # 'service_id', 'interface', and 'url'
        request_to_validate = {'service_id': uuid.uuid4().hex,
                               'interface': 'public',
                               'url': 'https://service.example.com:5000/'}
        self.create_endpoint_validator.validate(request_to_validate)

    def test_validate_endpoint_create_succeeds_with_valid_enabled(self):
        """Validate an endpoint with boolean values.

        Validate boolean values as `enabled` in endpoint create requests.
        """
        for valid_enabled in _VALID_ENABLED_FORMATS:
            request_to_validate = {'enable': valid_enabled,
                                   'service_id': uuid.uuid4().hex,
                                   'interface': 'public',
                                   'url': 'https://service.example.com:5000/'}
            self.create_endpoint_validator.validate(request_to_validate)

    def test_validate_create_endpoint_fails_with_invalid_enabled(self):
        """Exception raised when boolean-like values as `enabled`."""
        for invalid_enabled in _INVALID_ENABLED_FORMATS:
            request_to_validate = {'enable': invalid_enabled,
                                   'service_id': uuid.uuid4().hex,
                                   'interface': 'public',
                                   'url': 'https://service.example.com:5000/'}
            self.assertRaises(exception.SchemaValidationError,
                              self.create_endpoint_validator.validate,
                              request_to_validate)

    def test_validate_endpoint_create_succeeds_with_extra_parameters(self):
        """Test that extra parameters pass validation on create endpoint."""
        request_to_validate = {'other_attr': uuid.uuid4().hex,
                               'service_id': uuid.uuid4().hex,
                               'interface': 'public',
                               'url': 'https://service.example.com:5000/'}
        self.create_endpoint_validator.validate(request_to_validate)

    def test_validate_endpoint_create_fails_without_service_id(self):
        """Exception raised when `service_id` isn't in endpoint request."""
        request_to_validate = {'interface': 'public',
                               'url': 'https://service.example.com:5000/'}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_endpoint_validator.validate,
                          request_to_validate)

    def test_validate_endpoint_create_fails_without_interface(self):
        """Exception raised when `interface` isn't in endpoint request."""
        request_to_validate = {'service_id': uuid.uuid4().hex,
                               'url': 'https://service.example.com:5000/'}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_endpoint_validator.validate,
                          request_to_validate)

    def test_validate_endpoint_create_fails_without_url(self):
        """Exception raised when `url` isn't in endpoint request."""
        request_to_validate = {'service_id': uuid.uuid4().hex,
                               'interface': 'public'}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_endpoint_validator.validate,
                          request_to_validate)

    def test_validate_endpoint_create_fails_with_invalid_interface(self):
        """Exception raised with invalid `interface`."""
        request_to_validate = {'interface': uuid.uuid4().hex,
                               'service_id': uuid.uuid4().hex,
                               'url': 'https://service.example.com:5000/'}
        self.assertRaises(exception.SchemaValidationError,
                          self.create_endpoint_validator.validate,
                          request_to_validate)

    def test_validate_endpoint_update_fails_with_invalid_enabled(self):
        """Exception raised when `enabled` is boolean-like value."""
        for invalid_enabled in _INVALID_ENABLED_FORMATS:
            request_to_validate = {'enabled': invalid_enabled}
            self.assertRaises(exception.SchemaValidationError,
                              self.update_endpoint_validator.validate,
                              request_to_validate)

    def test_validate_endpoint_update_succeeds_with_valid_enabled(self):
        """Validate `enabled` as boolean values."""
        for valid_enabled in _VALID_ENABLED_FORMATS:
            request_to_validate = {'enabled': valid_enabled}
            self.update_endpoint_validator.validate(request_to_validate)

    def test_validate_endpoint_update_fails_with_invalid_interface(self):
        """Exception raised when invalid `interface` on endpoint update."""
        request_to_validate = {'interface': uuid.uuid4().hex,
                               'service_id': uuid.uuid4().hex,
                               'url': 'https://service.example.com:5000/'}
        self.assertRaises(exception.SchemaValidationError,
                          self.update_endpoint_validator.validate,
                          request_to_validate)

    def test_validate_endpoint_update_request_succeeds(self):
        """Test that we validate an endpoint update request."""
        request_to_validate = {'enabled': True,
                               'interface': 'admin',
                               'region_id': uuid.uuid4().hex,
                               'service_id': uuid.uuid4().hex,
                               'url': 'https://service.example.com:5000/'}
        self.update_endpoint_validator.validate(request_to_validate)

    def test_validate_endpoint_update_fails_with_no_parameters(self):
        """Exception raised when no parameters on endpoint update."""
        request_to_validate = {}
        self.assertRaises(exception.SchemaValidationError,
                          self.update_endpoint_validator.validate,
                          request_to_validate)

    def test_validate_endpoint_update_succeeds_with_extra_parameters(self):
        """Test that extra parameters pass validation on update endpoint."""
        request_to_validate = {'enabled': True,
                               'interface': 'admin',
                               'region_id': uuid.uuid4().hex,
                               'service_id': uuid.uuid4().hex,
                               'url': 'https://service.example.com:5000/',
                               'other_attr': uuid.uuid4().hex}
        self.update_endpoint_validator.validate(request_to_validate)
