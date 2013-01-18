import uuid

from keystone import config
from keystone import catalog
from keystone import test

import test_content_types


BASE_URL = 'http://127.0.0.1:35357/v2'
CONF = config.CONF


class V2CatalogTestCase(test_content_types.RestfulTestCase):
    def setUp(self):
        super(V2CatalogTestCase, self).setUp()
        self.service_id = uuid.uuid4().hex
        self.service = self.new_service_ref()
        self.service['id'] = self.service_id
        self.catalog_api.create_service(
            self.service_id,
            self.service.copy())

    def new_ref(self):
        """Populates a ref with attributes common to all API entities."""
        return {
            'id': uuid.uuid4().hex,
            'name': uuid.uuid4().hex,
            'description': uuid.uuid4().hex,
            'enabled': True}

    def new_service_ref(self):
        ref = self.new_ref()
        ref['type'] = uuid.uuid4().hex
        return ref

    def _get_token_id(self, r):
        """Applicable only to JSON."""
        return r.body['access']['token']['id']

    def assertValidErrorResponse(self, response):
        self.assertEqual(response.status, 400)

    def _endpoint_create(self, expected_status=200, missing_param=None):
        path = '/v2.0/endpoints'
        body = {
            "endpoint": {
                "adminurl": "http://localhost:8080",
                "service_id": self.service_id,
                "region": "regionOne",
                "internalurl": "http://localhost:8080",
                "publicurl": "http://localhost:8080"
            }
        }
        if missing_param:
            body['endpoint'][missing_param] = None
        r = self.admin_request(method='POST', token=self.get_scoped_token(),
                               path=path, expected_status=expected_status,
                               body=body)
        return body, r

    def test_endpoint_create(self):
        req_body, response = self._endpoint_create(expected_status=200)
        self.assertTrue('endpoint' in response.body)
        self.assertTrue('id' in response.body['endpoint'])
        for field, value in req_body['endpoint'].iteritems():
            self.assertEqual(response.body['endpoint'][field], value)

    def test_endpoint_create_with_missing_adminurl(self):
        req_body, response = self._endpoint_create(expected_status=200,
                                                   missing_param='adminurl')
        self.assertEqual(response.status, 200)

    def test_endpoint_create_with_missing_internalurl(self):
        req_body, response = self._endpoint_create(expected_status=200,
                                                   missing_param='internalurl')
        self.assertEqual(response.status, 200)

    def test_endpoint_create_with_missing_publicurl(self):
        req_body, response = self._endpoint_create(expected_status=400,
                                                   missing_param='publicurl')
        self.assertValidErrorResponse(response)


class EndpointMetadataTest(test.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_user_attributes_prefixed(self):
        attr = uuid.uuid4().hex
        ref = {
            'id': uuid.uuid4().hex,
            'name': uuid.uuid4().hex,
            attr: uuid.uuid4().hex}
        metadata = catalog.get_endpoint_metadata(user=ref)
        self.assertEqual(metadata['user_id'], ref['id'])
        self.assertEqual(metadata['user_name'], ref['name'])
        self.assertEqual(metadata['user_%s' % attr], ref[attr])

    def test_project_attributes_prefixed(self):
        attr = uuid.uuid4().hex
        ref = {
            'id': uuid.uuid4().hex,
            'name': uuid.uuid4().hex,
            attr: uuid.uuid4().hex}
        metadata = catalog.get_endpoint_metadata(project=ref)
        self.assertEqual(metadata['project_id'], ref['id'])
        self.assertEqual(metadata['project_name'], ref['name'])
        self.assertEqual(metadata['project_%s' % attr], ref[attr])

    def test_domain_attributes_prefixed(self):
        attr = uuid.uuid4().hex
        ref = {
            'id': uuid.uuid4().hex,
            'name': uuid.uuid4().hex,
            attr: uuid.uuid4().hex}
        metadata = catalog.get_endpoint_metadata(domain=ref)
        self.assertEqual(metadata['domain_id'], ref['id'])
        self.assertEqual(metadata['domain_name'], ref['name'])
        self.assertEqual(metadata['domain_%s' % attr], ref[attr])

    def test_conf_included_automatically(self):
        metadata = catalog.get_endpoint_metadata()
        self.assertIn('public_port', metadata)
        self.assertIn('admin_port', metadata)

    def test_admin_token_excluded(self):
        metadata = catalog.get_endpoint_metadata()
        self.assertNotIn('admin_token', metadata)

    def test_legacy_compatibility_for_tenant_id(self):
        ref = {'id': uuid.uuid4().hex}
        metadata = catalog.get_endpoint_metadata(project=ref)
        self.assertEqual(metadata['project_id'], ref['id'])
        self.assertEqual(metadata['tenant_id'], ref['id'])

    def test_format_url(self):
        user = {'id': uuid.uuid4().hex}
        project = {'id': uuid.uuid4().hex}
        domain = {'id': uuid.uuid4().hex}
        metadata = {'id': uuid.uuid4().hex}
        metadata = catalog.get_endpoint_metadata(
            user=user,
            project=project,
            domain=domain,
            metadata=metadata)

        url_template = (
            'http://localhost:%(admin_port)s/v2.0'
            '/metadata/%(id)s'
            '/domains/%(domain_id)s'
            '/projects/%(project_id)s'
            '/users/%(user_id)s')
        url = catalog.format_url(url_template, metadata)
        self.assertEquals(
            url,
            url_template % {
                'admin_port': CONF.admin_port,
                'id': metadata['id'],
                'user_id': user['id'],
                'project_id': project['id'],
                'domain_id': domain['id']})
