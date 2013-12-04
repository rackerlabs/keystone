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

import os
import random
import string
import uuid

from keystone.common.sql import migration
from keystone import config
from keystone import contrib
from keystone.openstack.common import importutils
from keystone.openstack.common import log
from keystone.tests import test_v3


CONF = config.CONF
LOG = log.getLogger(__name__)


def string_generator(size=255, chars=string.letters + string.digits):
    return ''.join(random.choice(chars) for x in range(size))


def dummy_validator(*args, **kwargs):
    pass


class FederationTests(test_v3.RestfulTestCase):

    EXTENSION_NAME = 'federation'
    EXTENSION_TO_ADD = 'federation_extension'

    def __init__(self, *args, **kwargs):
        super(FederationTests, self).__init__(*args, **kwargs)

    def setup_database(self):
        super(FederationTests, self).setup_database()
        package_name = "%s.%s.migrate_repo" % (contrib.__name__,
                                               self.EXTENSION_NAME)
        package = importutils.import_module(package_name)
        self.repo_path = os.path.abspath(os.path.dirname(package.__file__))
        migration.db_version_control(version=None, repo_path=self.repo_path)
        migration.db_sync(version=None, repo_path=self.repo_path)


class FederatedIdentityProviderTests(FederationTests):
    """A test class for Identity Providers."""

    minimum_idp_keys = ['name', 'description', 'enabled']
    full_idp_keys = minimum_idp_keys
    public_keys_keys = ['id', 'key']

    default_body = {'name': None,
                    'description': None,
                    'enabled': True}

    def base_url(self, suffix=''):
        return '/OS-IDP/identity_providers' + suffix

    def _fetch_attribute_from_response(self, resp, parameter,
                                       assertNone=True):
        """Fetch single attribute from TestResponse object."""
        result = resp.result.get(parameter, None)
        if assertNone:
            self.assertIsNotNone(result)
        return result

    def _fetch_attributes_from_response(self, resp, parameters=[],
                                        assertNone=True):
        """Fetch parameters from the TestResponse object."""

        result = dict()
        for parameter in parameters:
            value = self._fetch_attribute_from_response(resp,
                                                        parameter,
                                                        assertNone=assertNone)
            result[parameter] = value
        return result

    def _create_and_decapsulate_response(self, body=None):
        default_resp = self._create_default_idp(body=body)
        idp = self._fetch_attribute_from_response(default_resp,
                                                  'identity_provider')
        self.assertIsNotNone(idp)
        idp_id = idp.get('id')
        self.assertIsNotNone(idp_id)
        return (str(idp_id), idp)

    def _get_idp(self, idp_id):
        url = self.base_url(suffix='/%(idp_id)s')
        url = url % {'idp_id': idp_id}
        resp = self.get(url)
        return resp

    def _create_default_idp(self, body=None):
        """Create default IdP."""

        url = self.base_url()
        if body is None:
            body = self._http_input()
        body = {'identity_provider': body}

        resp = self.post(url, body=body)
        self.assertResponseStatus(resp, 201)
        return resp

    def _http_input(self, **kwargs):
        body = None
        if 'body' not in kwargs:
            body = FederatedIdentityProviderTests.default_body.copy()
            body['name'] = string_generator()
            body['description'] = string_generator()
        else:
            body = kwargs['body']
        return body

    def _assign_protocol_to_idp(self, idp_id=None, proto=None, url=None,
                                mapping_id=None, validate=True, **kwargs):
        if url is None:
            url = self.base_url(suffix='/%(idp_id)s/protocols')
        if idp_id is None:
            idp_id, _ = self._create_and_decapsulate_response()
        if proto is None:
            proto = string_generator(size=8)
        if mapping_id is None:
            mapping_id = string_generator(size=8)
        body = {'id': proto,
                'mapping_id': mapping_id}
        url = url % {'idp_id': idp_id}
        resp = self.put(url, body={'protocol': body}, **kwargs)
        if validate:
            self.assertValidResponse(resp, 'protocol', dummy_validator,
                                     keys_to_check=['id', 'mapping_id'],
                                     ref={'id': proto,
                                          'mapping_id': mapping_id})
        return (resp, idp_id, proto)

    def _get_protocol(self, idp_id, protocol_id):
        url = self.base_url(suffix='/%(idp_id)s/'
                                   'protocols/%(protocol_id)s')
        url = url % {'idp_id': idp_id,
                     'protocol_id': protocol_id}
        r = self.get(url)
        return r

    def test_create_idp(self):
        """Creates the IdentityProvider entity."""

        keys_to_check = self.minimum_idp_keys
        body = self._http_input()
        resp = self._create_default_idp(body=body)
        self.assertValidResponse(resp, 'identity_provider', dummy_validator,
                                 keys_to_check=keys_to_check,
                                 ref=body)

    def test_list_idps(self, iterations=5):
        """Lists all available IdentityProviders.

        This test collects ids of created IdPs and
        intersects it with the list of all available IdPs.
        List of all IdPs can be a superset of IdPs created in this test,
        because other tests also create IdPs.

        """
        def get_id(resp):
            r = self._fetch_attribute_from_response(resp,
                                                    'identity_provider')
            return r.get('id')

        url = self.base_url()
        ids = []
        for _ in xrange(iterations):
            id = get_id(self._create_default_idp())
            ids.append(id)
        ids = set(ids)

        keys_to_check = FederatedIdentityProviderTests.full_idp_keys
        resp = self.get(url)
        self.assertValidListResponse(resp, 'identity_providers',
                                     dummy_validator,
                                     keys_to_check=keys_to_check)
        entities = self._fetch_attribute_from_response(resp,
                                                       'identity_providers')
        entities_ids = set([e['id'] for e in entities])
        ids_intersect = entities_ids & ids
        self.assertEqual(len(ids_intersect), len(ids))

    def test_get_idp(self):

        url = self.base_url(suffix='/%(idp_id)s')
        body = self._http_input()
        default_resp = self._create_default_idp(body=body)

        default_idp = self._fetch_attribute_from_response(default_resp,
                                                          'identity_provider')
        idp_id = default_idp.get('id')

        self.assertIsNotNone(idp_id)

        url = url % {'idp_id': str(idp_id)}
        resp = self.get(url)
        self.assertValidResponse(resp, 'identity_provider',
                                 dummy_validator, keys_to_check=body.keys(),
                                 ref=body)

    def test_get_nonexisting_idp(self):
        url = self.base_url(suffix='/%(idp_id)s')
        idp_id = uuid.uuid4().hex
        self.assertIsNotNone(idp_id)

        url = url % {'idp_id': str(idp_id)}
        self.get(url, expected_status=404)

    def test_delete_existing_idp(self):
        url = self.base_url(suffix='/%(idp_id)s')
        default_resp = self._create_default_idp()
        default_idp = self._fetch_attribute_from_response(default_resp,
                                                          'identity_provider')

        idp_id = default_idp.get('id')
        self.assertIsNotNone(idp_id)

        url = url % {'idp_id': str(idp_id)}
        self.delete(url)

        self.get(url, expected_status=404)

    def test_delete_nonexisting_idp(self):
        url = self.base_url(suffix='/%(idp_id)s')
        idp_id = uuid.uuid4().hex

        url = url % {'idp_id': str(idp_id)}
        self.delete(url, expected_status=404)

    def test_update_idp_mutable_attributes(self):
        url = self.base_url(suffix='/%(idp_id)s')
        default_resp = self._create_default_idp()
        default_idp = self._fetch_attribute_from_response(default_resp,
                                                          'identity_provider')
        idp_id = default_idp.get('id')
        self.assertIsNotNone(idp_id)

        url = url % {'idp_id': str(idp_id)}
        _enabled = not default_idp.get('enabled')
        body = {'name': string_generator(),
                'description': string_generator(),
                'enabled': _enabled}

        body = {'identity_provider': body}
        resp = self.patch(url, body=body)
        updated_idp = self._fetch_attribute_from_response(resp,
                                                          'identity_provider')
        body = body['identity_provider']
        for key in body.keys():
            self.assertEqual(body[key], updated_idp.get(key))

        resp = self.get(url)
        updated_idp = self._fetch_attribute_from_response(resp,
                                                          'identity_provider')
        for key in body.keys():
            self.assertEqual(body[key], updated_idp.get(key))

    def test_update_idp_immutable_attributes(self):
        url = self.base_url(suffix='/%(idp_id)s')
        default_resp = self._create_default_idp()
        default_idp = self._fetch_attribute_from_response(default_resp,
                                                          'identity_provider')
        idp_id = default_idp.get('id')
        self.assertIsNotNone(idp_id)

        body = self._http_input()
        body['id'] = string_generator(size=64)
        body['protocols'] = ['a', 'b']
        body = {'identity_provider': body}

        url = url % {'idp_id': str(idp_id)}
        self.patch(url, body=body, expected_status=400)

    def test_update_nonexistent_idp(self):
        url = self.base_url(suffix='/%(idp_id)s')
        idp_id = uuid.uuid4().hex
        url = url % {'idp_id': idp_id}
        body = self._http_input()
        body['enabled'] = False
        body = {'identity_provider': body}

        self.patch(url, body=body, expected_status=404)

    def test_assign_protocol_to_idp(self):
        resp, idp_id, proto = self._assign_protocol_to_idp(expected_status=200)

    def test_protocol_composite_pk(self):
        """Check whether Keystone let's add two entities with identical
        names, however attached to diferent IdPs.

        1. Add IdP and assign it protocol with predefined name
        2. Add another IdP and assign it a protocol with same name.
        Expected result HTTP 200/204

        """
        url = self.base_url(suffix='/%(idp_id)s/protocols')

        kwargs = {'expected_status': 200}
        resp, idp_id, proto = self._assign_protocol_to_idp(proto='saml2',
                                                           url=url, **kwargs)

        resp, idp_id, proto = self._assign_protocol_to_idp(proto='saml2',
                                                           url=url, **kwargs)

    def test_protocol_idp_pk_uniqueness(self):
        """Test whether Keystone checks for unique idp/protocol values.

        Add same protocol twice, expect Keystone to reject a request
        with HTTP 409 response code.

        """
        url = self.base_url(suffix='/%(idp_id)s/protocols')

        kwargs = {'expected_status': 200}
        resp, idp_id, proto = self._assign_protocol_to_idp(proto='saml2',
                                                           url=url, **kwargs)

        kwargs = {'expected_status': 409}
        resp, idp_id, proto = self._assign_protocol_to_idp(idp_id=idp_id,
                                                           proto='saml2',
                                                           validate=False,
                                                           url=url, **kwargs)

    def test_assign_protocol_to_nonexistent_idp(self):
        """Try tying protocol to IdP that doesn't exist."""

        idp_id = string_generator(size=16)
        kwargs = {'expected_status': 404}
        self._assign_protocol_to_idp(proto='saml2',
                                     idp_id=idp_id,
                                     validate=False,
                                     **kwargs)

    def test_get_protocol(self):

        url = self.base_url(suffix='/%(idp_id)s/'
                                   'protocols/%(protocol_id)s')
        resp, idp_id, proto = self._assign_protocol_to_idp(expected_status=200)
        proto_id = self._fetch_attribute_from_response(resp, 'protocol')['id']

        url = url % {'idp_id': idp_id,
                     'protocol_id': proto_id}
        resp = self.get(url)

        reference = {'id': proto_id}
        self.assertValidResponse(resp, 'protocol',
                                 dummy_validator,
                                 keys_to_check=reference.keys(),
                                 ref=reference)

    def test_list_protocols(self):
        url = self.base_url(suffix='/%(idp_id)s/protocols/')
        resp, idp_id, proto = self._assign_protocol_to_idp(expected_status=200)
        iterations = random.randint(0, 16)
        protocol_ids = []
        for _ in xrange(iterations):
            resp, _, proto = self._assign_protocol_to_idp(idp_id=idp_id,
                                                          expected_status=200)
            proto_id = self._fetch_attribute_from_response(resp, 'protocol')
            proto_id = proto_id['id']
            protocol_ids.append(proto_id)

        url = url % {'idp_id': idp_id}
        resp = self.get(url)
        self.assertValidListResponse(resp, 'protocols',
                                     dummy_validator,
                                     keys_to_check=['id'])
        entities = self._fetch_attribute_from_response(resp, 'protocols')
        entities = set([entity['id'] for entity in entities])
        intersection = entities & set(protocol_ids)
        self.assertEqual(len(intersection), len(protocol_ids))

    def test_update_protocols_attribute(self):
        url = self.base_url(suffix='/%(idp_id)s/'
                                   'protocols/%(protocol_id)s')

        resp, idp_id, proto = self._assign_protocol_to_idp(expected_status=200)
        new_mapping_id = string_generator(size=64)
        url = url % {'idp_id': idp_id,
                     'protocol_id': proto}
        body = {'mapping_id': new_mapping_id}
        resp = self.patch(url, body={'protocol': body})
        self.assertValidResponse(resp, 'protocol', dummy_validator,
                                 keys_to_check=['id', 'mapping_id'],
                                 ref={'id': proto,
                                      'mapping_id': new_mapping_id})

    def test_delete_protocol(self):

        url = self.base_url(suffix='/%(idp_id)s/'
                                   'protocols/%(protocol_id)s')
        resp, idp_id, proto = self._assign_protocol_to_idp(expected_status=200)
        url = url % {'idp_id': idp_id,
                     'protocol_id': proto}
        self.delete(url)
        self.get(url, expected_status=404)
