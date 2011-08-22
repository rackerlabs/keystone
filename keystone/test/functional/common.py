import unittest2 as unittest
import httplib
import uuid
import json
from lxml import etree


class HttpTestCase(unittest.TestCase):
    """Performs generic HTTP request testing"""

    def request(self, host='127.0.0.1', port=80, method='GET', path='/',
            headers=None, body=None, assert_status=None):
        """Perform request and fetch httplib.HTTPResponse from the server"""

        # Initialize headers dictionary
        headers = {} if not headers else headers

        # Initialize a connection
        connection = httplib.HTTPConnection(host, port, timeout=3)

        # Perform the request
        connection.request(method, path, body, headers)

        # Retrieve the response so can go ahead and close the connection
        response = connection.getresponse()
        response.body = response.read()

        # Close the connection
        connection.close()

        # Automatically assert HTTP status code
        if assert_status:
            self.assertResponseStatus(response, assert_status)
        else:
            self.assertResponseSuccessful(response)

        # Contains the response headers, body, etc
        return response

    def assertResponseSuccessful(self, response):
        """Asserts that a status code lies inside the 2xx range"""
        self.assertTrue(response.status >= 200 and response.status <= 299,
            'Status code %d is outside of the expected range (2xx)\n\n%s' %
            (response.status, response.body))

    def assertResponseStatus(self, response, assert_status):
        """Asserts a specific status code on the response"""
        self.assertEqual(response.status, assert_status,
            'Status code %s is not %s, as expected)\n\n%s' %
            (response.status, assert_status, response.body))


class RestfulTestCase(HttpTestCase):
    """Performs restful HTTP request testing"""

    def restful_request(self, headers=None, as_json=None, as_xml=None,
        **kwargs):
        """Encodes and decodes (JSON & XML) HTTP requests and responses.

        Dynamically encodes json or xml as request body if one is provided.

        WARNING: Existing Content-Type header will be overwritten.
        WARNING: If both as_json and as_xml are provided, as_xml is ignored.
        WARNING: If either as_json or as_xml AND a body is provided, the body
            is ignored.

        Dynamically returns 'as_json' or 'as_xml' attribute based on the
        detected response type, and fails the current test case if
        unsuccessful.

        response.as_json: standard python dictionary
        response.as_xml: as_etree.ElementTree
        """

        # Initialize headers dictionary
        headers = {} if not headers else headers

        # Attempt to encode JSON and XML automatically, if requested
        if as_json:
            body = RestfulTestCase._encode_json(as_json)
            headers['Content-Type'] = 'application/json'
        elif as_xml:
            body = as_xml
            headers['Content-Type'] = 'application/xml'
        else:
            body = kwargs.get('body')

        # Perform the HTTP request/response
        response = self.request(headers=headers, body=body, **kwargs)

        # Attempt to parse JSON and XML automatically, if detected
        response = self._decode_response_body(response)

        # Contains the decoded response as_json/as_xml, etc
        return response

    @staticmethod
    def _encode_json(data):
        """Returns a JSON-encoded string of the given python dictionary"""
        return json.dumps(data)

    def _decode_response_body(self, response):
        """Detects response body type, and attempts to decode it"""
        if 'application/json' in response.getheader('Content-Type'):
            response.json = self._decode_json(response.body)
        elif 'application/xml' in response.getheader('Content-Type'):
            response.xml = self._decode_xml(response.body)
        return response

    @staticmethod
    def _decode_json(json_str):
        """Returns a dict of the given JSON string"""
        return json.loads(json_str)

    @staticmethod
    def _decode_xml(xml_str):
        """Returns an ElementTree of the given XML string"""
        return etree.ElementTree.fromstring(xml_str)


class KeystoneTestCase(RestfulTestCase):
    """Abstracts REST verbs & resources of the service & admin API."""

    def service_request(self, version='2.0', path='', port=5000, headers=None,
            **kwargs):
        """Returns a request to the service API"""

        # Initialize headers dictionary
        headers = {} if not headers else headers

        path = KeystoneTestCase._version_path(version, path)

        if self.service_token:
            headers['X-Auth-Token'] = self.service_token

        return self.restful_request(port=port, path=path, headers=headers,
            **kwargs)

    def admin_request(self, version='2.0', path='', port=5001, headers=None,
            **kwargs):
        """Returns a request to the admin API"""

        # Initialize headers dictionary
        headers = {} if not headers else headers

        path = KeystoneTestCase._version_path(version, path)

        if self.admin_token:
            headers['X-Auth-Token'] = self.admin_token

        return self.restful_request(port=port, path=path, headers=headers,
            **kwargs)

    @staticmethod
    def _version_path(version, path):
        """Prepend the given path with the API version.

        An empty version results in no version being prepended."""
        if version:
            return '/v' + str(version) + str(path)
        else:
            return str(path)

    def post_token(self, **kwargs):
        """POST /tokens"""
        return self.service_request(method='POST', path='/tokens', **kwargs)

    def get_token(self, token_id, **kwargs):
        """GET /tokens/{token_id}"""
        return self.admin_request(method='GET',
            path='/tokens/%s' % (token_id,), **kwargs)

    def delete_token(self, token_id, **kwargs):
        """DELETE /tokens/{token_id}"""
        return self.admin_request(method='DELETE',
            path='/tokens/%s' % (token_id,), **kwargs)

    def post_tenant(self, **kwargs):
        """POST /tenants"""
        return self.admin_request(method='POST', path='/tenants', **kwargs)

    def get_tenants(self, **kwargs):
        """GET /tenants"""
        return self.admin_request(method='GET', path='/tenants', **kwargs)

    def get_tenant(self, tenant_id, **kwargs):
        """GET /tenants/{tenant_id}"""
        return self.admin_request(method='GET',
            path='/tenants/%s' % (tenant_id,), **kwargs)

    def get_tenant_users(self, tenant_id, **kwargs):
        """GET /tenants/{tenant_id}/users"""
        return self.admin_request(method='GET',
            path='/tenants/%s' % (tenant_id,), **kwargs)

    def delete_tenant(self, tenant_id, **kwargs):
        """DELETE /tenants/{tenant_id}"""
        return self.admin_request(method='DELETE',
            path='/tenants/%s' % (tenant_id,), **kwargs)

    def post_user(self, **kwargs):
        """POST /users"""
        return self.admin_request(method='POST', path='/users', **kwargs)

    def get_users(self, **kwargs):
        """GET /users"""
        return self.admin_request(method='GET', path='/users', **kwargs)

    def get_user(self, user_id, **kwargs):
        """GET /users/{user_id}"""
        return self.admin_request(method='GET',
            path='/users/%s' % (user_id,), **kwargs)

    def query_user(self, user_name, **kwargs):
        """GET /users?username={user_name}"""
        return self.admin_request(method='GET',
            path='/users?username=%s' % (user_name,), **kwargs)

    def put_user(self, user_id, **kwargs):
        """PUT /users/{user_id}"""
        return self.admin_request(method='PUT',
            path='/users/%s' % (user_id,), **kwargs)

    def put_user_password(self, user_id, **kwargs):
        """PUT /users/{user_id}/password"""
        return self.admin_request(method='PUT',
            path='/users/%s/password' % (user_id,), **kwargs)

    def put_user_tenant(self, user_id, **kwargs):
        """PUT /users/{user_id}/tenant"""
        return self.admin_request(method='PUT',
            path='/users/%s/tenant' % (user_id,), **kwargs)

    def put_user_enabled(self, user_id, **kwargs):
        """PUT /users/{user_id}/enabled"""
        return self.admin_request(method='PUT',
            path='/users/%s/enabled' % (user_id,), **kwargs)

    def delete_user(self, user_id, **kwargs):
        """DELETE /users/{user_id}"""
        return self.admin_request(method='DELETE',
            path='/users/%s' % (user_id,), **kwargs)

    def get_user_role(self, user_id, **kwargs):
        """GET /users/{user_id}/roleRefs"""
        return self.admin_request(method='GET',
            path='/users/%s/roleRefs' % (user_id,), **kwargs)

    def post_user_role(self, user_id, **kwargs):
        """POST /users/{user_id}/roleRefs"""
        return self.admin_request(method='POST',
            path='/users/%s/roleRefs' % (user_id,), **kwargs)

    def delete_user_role(self, user_id, role_id, **kwargs):
        """DELETE /users/{user_id}/roleRefs/{role_ref_id}"""
        return self.admin_request(method='DELETE',
            path='/users/%s/roleRefs/%s' % (user_id, role_id), **kwargs)

    def post_role(self, **kwargs):
        """POST /roles"""
        return self.admin_request(method='POST', path='/roles', **kwargs)

    def get_roles(self, **kwargs):
        """GET /roles"""
        return self.admin_request(method='GET', path='/roles', **kwargs)

    def get_role(self, role_id, **kwargs):
        """GET /roles/{role_id}"""
        return self.admin_request(method='GET',
            path='/roles/%s' % (role_id,), **kwargs)

    def delete_role(self, role_id, **kwargs):
        """DELETE /roles/{role_id}"""
        return self.admin_request(method='DELETE',
            path='/roles/%s' % (role_id,), **kwargs)

    def get_endpoint_templates(self, **kwargs):
        """GET /endpointTemplates"""
        return self.admin_request(method='GET', path='/endpointTemplates',
            **kwargs)

    def post_endpoint_template(self, **kwargs):
        """POST /endpointTemplates"""
        return self.admin_request(method='POST', path='/endpointTemplates',
            **kwargs)

    def put_endpoint_template(self, endpoint_template_id, **kwargs):
        """PUT /endpointTemplates/{endpoint_template_id}"""
        return self.admin_request(method='PUT',
            path='/endpointTemplates/%s' % (endpoint_template_id,),
            **kwargs)

    def get_endpoint_template(self, endpoint_template_id, **kwargs):
        """GET /endpointTemplates/{endpoint_template_id}"""
        return self.admin_request(method='GET',
            path='/endpointTemplates/%s' % (endpoint_template_id,),
            **kwargs)

    def delete_endpoint_template(self, endpoint_template_id, **kwargs):
        """DELETE /endpointTemplates/{endpoint_template_id}"""
        return self.admin_request(method='DELETE',
            path='/endpointTemplates/%s' % (endpoint_template_id,),
            **kwargs)

    def get_tenant_endpoints(self, tenant_id, **kwargs):
        """GET /tenants/{tenant_id}/endpoints"""
        return self.admin_request(method='GET',
            path='/tenants/%s/endpoints' % (tenant_id,),
            **kwargs)

    def post_tenant_endpoint(self, tenant_id, **kwargs):
        """POST /tenants/{tenant_id}/endpoints"""
        return self.admin_request(method='POST',
            path='/tenants/%s/endpoints' % (tenant_id,), **kwargs)

    def delete_tenant_endpoint(self, tenant_id, endpoint_id, **kwargs):
        """DELETE /tenants/{tenant_id}/endpoints/{endpoint_id}"""
        return self.admin_request(method='DELETE',
            path='/tenants/%s/endpoints/%s' % (tenant_id, endpoint_id,),
            **kwargs)

    def post_service(self, **kwargs):
        """POST /services"""
        return self.admin_request(method='POST', as_json='/services', **kwargs)

    def get_services(self, **kwargs):
        """GET /services"""
        return self.admin_request(method='GET', as_json='/services', **kwargs)

    def get_service(self, service_id, **kwargs):
        """GET /services/{service_id}"""
        return self.admin_request(method='GET',
            path='/services/%s' % (service_id,), **kwargs)

    def delete_service(self, service_id, **kwargs):
        """DELETE /services/{service_id}"""
        return self.admin_request(method='DELETE',
            path='/services/%s' % (service_id,), **kwargs)

    def get_root(self, **kwargs):
        """GET /"""
        return self.service_request(method='GET', path='/', **kwargs)

    def get_extensions(self, **kwargs):
        """GET /extensions"""
        return self.service_request(method='GET', path='/extensions', **kwargs)

    def get_admin_guide(self, **kwargs):
        """GET /identityadminguide.pdf"""
        return self.service_request(method='GET', path='/identityadminguide.pdf',
            **kwargs)

    def get_admin_wadl(self, **kwargs):
        """GET /identity-admin.wadl"""
        return self.service_request(method='GET', path='/identity-admin.wadl',
            **kwargs)

    def get_common_ent(self, **kwargs):
        """GET /common.ent"""
        return self.service_request(method='GET', path='/common.ent',
            **kwargs)

    def get_xsd(self, filename, **kwargs):
        """GET /xsd/{xsd}"""
        return self.service_request(method='GET', path='/xsd/%s' % (filename,),
            **kwargs)

    def get_xsd_atom(self, filename, **kwargs):
        """GET /xsd/atom/{xsd}"""
        return self.service_request(method='GET',
            path='/xsd/atom/%s' % (filename,), **kwargs)

    def get_xslt(self, filename, **kwargs):
        """GET /xslt/{file:.*}"""
        return self.service_request(method='GET', path='/xslt/%s' % (filename,),
            **kwargs)

    def get_javascript(self, filename, **kwargs):
        """GET /js/{file:.*}"""
        return self.service_request(method='GET', path='/js/%s' % (filename,),
            **kwargs)

    def get_style(self, filename, **kwargs):
        """GET /style/{file:.*}"""
        return self.service_request(method='GET', path='/style/%s' % (filename,),
            **kwargs)

    def get_sample(self, filename, **kwargs):
        """GET /samples/{file:.*}"""
        return self.service_request(method='GET',
            path='/samples/%s' % (filename,), **kwargs)


# Generates and return a unique string
unique_str = (lambda: str(uuid.uuid4()))

# Automatically populates optional string fields
optional_str = (lambda x: x if x is not None else unique_str())


class KeystoneClientTestCase(KeystoneTestCase):
    """Abstracts CRUD of the keystone API"""
    service_token = None

    admin_token = None
    admin_username = 'admin'
    admin_password = 'secrete'

    def setUp(self):
        """Prepare keystone for system tests"""
        # Authenticate as admin user to establish admin_token
        self.admin_token = self.authenticate(self.admin_username,
            self.admin_password)

    def authenticate(self, user_name=None, user_password=None, tenant_id=None):
        user_name = optional_str(user_name)
        user_password = optional_str(user_password)

        data = {
            "passwordCredentials": {
                "username": user_name,
                "password": user_password}}

        if tenant_id:
            data["passwordCredentials"]["tenantId"] = tenant_id

        return self.post_token(as_json=data).json['auth']['token']['id']

    def validate_token(self, token_id=None):
        token_id = optional_str(token_id)

        return self.get_token(token_id)

    def remove_token(self, token_id=None):
        token_id = optional_str(token_id)

        return self.delete_token(token_id)

    def create_tenant(self, tenant_name=None, tenant_description=None,
            tenant_enabled=True):
        tenant_name = optional_str(tenant_name)
        tenant_description = optional_str(tenant_description)

        data = {
            "tenant": {
                "name": tenant_name,
                "description": tenant_description,
                "enabled": tenant_enabled}}

        return self.post_tenant(as_json=data).json['tenant']['id']

    def list_tenants(self):
        return self.get_tenants()

    def fetch_tenant(self, tenant_id):
        tenant_id = optional_str(tenant_id)

        return self.get_tenant(tenant_id)

    def list_tenant_users(self, tenant_id):
        tenant_id = optional_str(tenant_id)

        return self.get_tenant_users(tenant_id)

    def remove_tenant(self, tenant_id=None):
        tenant_id = optional_str(tenant_id)

        return self.delete_tenant(tenant_id)

    def create_user(self, user_name=None, user_email=None, user_password=None,
            tenant_id=None, user_enabled=True):
        user_name = optional_str(user_name)
        user_email = user_email or (user_name + '@openstack.org')
        user_password = optional_str(user_password)

        data = {
            "user": {
                "password": user_password,
                "name": user_name,
                "tenantId": tenant_id,
                "email": user_email,
                "enabled": user_enabled}}

        return self.post_user(as_json=data).json['user']['id']

    def list_users(self):
        return self.get_users()

    def fetch_user(self, user_id=None):
        user_id = optional_str(user_id)

        return self.get_user(user_id)

    def fetch_user_by_name(self, user_name=None):
        user_name = optional_str(user_name)

        return self.query_user(user_name)

    def update_user(self, user_id=None, user_email=None, user_enabled=None):
        user_id = optional_str(user_id)

        data = {"user": {}}

        if user_email is not None:
            data['user']['email'] = user_email

        if user_enabled is not None:
            data['user']['enabled'] = user_enabled

        self.put_user(user_id, as_json=data)

    def set_user_password(self, user_id=None, user_password=None):
        user_id = optional_str(user_id)
        user_password = optional_str(user_password)

        data = {"user": {"password": user_password}}
        self.put_user_password(user_id, as_json=data)

    def set_user_tenant(self, user_id=None, tenant_id=None):
        user_id = optional_str(user_id)
        tenant_id = optional_str(tenant_id)

        data = {"user": {"tenantId": tenant_id}}
        self.put_user_tenant(user_id, as_json=data)

    def _enable_disable_user(self, user_id, user_enabled):
        """Private function to enable and disable a user.
        
        Use enable_user() and disable_user() instead."""
        data = {"user": {"enabled": user_enabled}}

        self.put_user_enabled(user_id, as_json=data)

    def enable_user(self, user_id=None):
        user_id = optional_str(user_id)

        self.enable_disable_user(user_id, True)

    def disable_user(self, user_id=None):
        user_id = optional_str(user_id)

        self.enable_disable_user(user_id, False)

    def remove_user(self, user_id=None):
        user_id = optional_str(user_id)

        self.delete_user(user_id)

    def grant_role_to_user(self, user_id=None, role_id=None, tenant_id=None):
        user_id = optional_str(user_id)
        role_id = optional_str(role_id)
        tenant_id = optional_str(tenant_id)

        data = {
            "roleRef": {
                "tenantId": tenant_id,
                "roleId": role_id}}

        self.post_user_role(user_id, as_json=data)

    def revoke_role_from_user(self, user_id=None, role_id=None):
        user_id = optional_str(user_id)
        role_id = optional_str(role_id)

        self.delete_user_role(user_id, role_id)

    def create_role(self, role_id=None, role_description=None,
            service_id=None):
        role_id = optional_str(role_id)
        role_description = optional_str(role_description)

        data = {
            "role": {
                "id": role_id,
                "description": role_description}}

        if service_id is not None:
            data['role']['serviceId'] = service_id

        self.post_role(as_json=data)

    def list_roles(self):
        return self.get_roles()

    def fetch_role(self, role_id=None):
        role_id = optional_str(role_id)

        return self.get_role(role_id)

    def remove_role(self, role_id=None):
        role_id = optional_str(role_id)

        self.delete_role(role_id)

    def create_service(self, service_id=None, service_description=None):
        service_id = optional_str(service_id)
        service_description = optional_str(service_description)

        data = {
            "service": {
                "id": service_id,
                "description": service_description}}
        self.post_service(as_json=data)

    def list_services(self):
        return self.get_services()

    def fetch_service(self, service_id=None):
        service_id = optional_str(service_id)

        return self.get_service(service_id)

    def remove_service(self, service_id=None):
        service_id = optional_str(service_id)

        self.delete_service(service_id)

    def add_endpoint_to_tenant(self, tenant_id=None,
            endpoint_template_id=None):
        tenant_id = optional_str(tenant_id)
        endpoint_template_id = optional_str(endpoint_template_id)

        data = {"endpointTemplate": {"id": endpoint_template_id}}

        return self.post_tenant_endpoint(tenant_id, endpoint_template_id,
            as_json=data)

    def list_tenant_endpoints(self, tenant_id=None):
        tenant_id = optional_str(tenant_id)

        self.get_tenant_endpoints(tenant_id)

    def remove_endpoint_from_tenant(self, tenant_id=None, endpoint_id=None):
        tenant_id = optional_str(tenant_id)
        endpoint_id = optional_str(endpoint_id)

        """TODO: Should this be an 'endpoint_id' or 'endpoint_template_id'??"""
        self.delete_tenant_endpoint(tenant_id, endpoint_id)

    def remove_tenant_endpoint(self, tenant_id=None, endpoint_id=None):
        tenant_id = optional_str(tenant_id)
        endpoint_id = optional_str(endpoint_id)

        """TODO: Should this be an 'endpoint_id' or 'endpoint_template_id'??"""
        self.delete_tenant_endpoint(tenant_id, endpoint_id)

    def remove_all_endpoints_for_tenant(self, tenant_id=None):
        tenant_id = optional_str(tenant_id)

        self.delete_tenant_endpoints(tenant_id)


def delete_all_endpoint(tenant_id):
    (resp, content) = header.request(url, "GET", body='{}',
                              headers={"Content-Type": "application/json"})

    obj = json.loads(content)
    try:
        endpoints = obj["endpoints"]["values"]
    except KeyError:
        pass
    else:
        for endpoint in endpoints:
            delete_endpoint(tenant_id, endpoint["id"])


def create_endpoint_template(region, service, public_url, admin_url,
        internal_url, enabled, is_global):
    url = '/endpointTemplates'
    body = {"endpointTemplate": {"region": region,
                       "serviceId": service,
                       "publicURL": public_url,
                       "adminURL": admin_url,
                       "internalURL": internal_url,
                       "enabled": enabled,
                       "global": is_global}}
    return header.request(url, "POST", body=json.dumps(body),
                              headers={"Content-Type": "application/json"})


def delete_endpoint_template(endpoint_template_id):

    url = '/endpointTemplates/%s' % (endpoint_template_id)
    return header.request(url, "DELETE", body='',
                              headers={"Content-Type": "application/json"})


def update_endpoint_template(endpoint_template_id, region, service,
    public_url, admin_url, internal_url, enabled, is_global):


    url = '/endpointTemplates/%s' % (endpoint_template_id)
    body = {"endpointTemplate": {"region": region,
                       "serviceId": service,
                       "publicURL": public_url,
                       "adminURL": admin_url,
                       "internalURL": internal_url,
                       "enabled": enabled,
                       "global": is_global}}
    return header.request(url, "PUT", body=json.dumps(body),
                              headers={"Content-Type": "application/json"})


def get_endpoint_template(endpoint_template_id):
    url = '/endpointTemplates/%s' % (endpoint_template_id,)
    #test for Content-Type = application/json
    return header.request(url, "GET", body='{}',
        headers={"Content-Type": "application/json"})


def content_type(resp):
    return resp['content-type'].split(';')[0]

def get_global_tenant():
    return 'GlobalTenant'

class FunctionalTest(unittest.TestCase):
    """Base functional test case for Keystone"""
    admin_token = str('999888777666')
    service_token = None
    exp_auth_token = str('000999')
    disabled_token = str('999888777')
    missing_token = str('')
    invalid_token = str('invalid_token')

    def setUp(self):
        self.service_id = unique_str()
        self.service_role = self.service_id + ':test_role'

        self.tenant_name = unique_str()

        self.user_id = None
        self.user_name = unique_str()
        self.user_password = unique_str()
        self.user_email = self.user_name + '@openstack.org'

        self.disabled_user_id = None
        self.disabled_user_name = unique_str()
        self.disabled_user_password = unique_str()
        self.disabled_user_email = self.disabled_user_name + '@openstack.org'

        # Create a tenant
        self.tenant_id = self.create_tenant(self.tenant_name)

        # Create a user attached to the above tenant
        self.user_id = self.create_user(self.user_name, self.user_password,
            self.user_email, self.tenant_id)

        # Authenticate the above user for his tenant
        self.service_token = get_token(self.user_name, self.user_password,
            self.tenant_id, 'token')

        # Create and disable a user
        self.disabled_user_id = self.create_user(self.disabled_user_name,
            self.user_password, self.disabled_user_email, self.tenant_id)
        user_set_enabled(self.admin_token, self.disabled_user_id,
            enabled=False)

    def tearDown(self):
        delete_token(self.service_token, self.admin_token)
        self.delete_user(self.user_id)
        delete_tenant(self.tenant_id, self.admin_token)

    def assertStatusCode(self, code, resp, content):
        self.assertEqual(code, int(resp['status']), (resp, content))

    def assertContentType(self, content_type, resp, content):
        self.assertEqual(content_type, resp['content-type'].split(';')[0],
            (resp, content))

    # User shortcuts

    def create_user(self, username, password, email, tenant_id):
        resp, content = create_user_json(tenant_id, username, self.admin_token,
            email, password)
        self.assertStatusCode(201, resp, content)
        self.assertContentType('application/json', resp, content)
        return json.loads(content)['user']['id']

    def delete_user(self, user_id):
        url = '/users/%s' % (user_id)
        resp, content = header.request(url, "DELETE", body='{}', headers={
            "Content-Type": "application/json"})
        self.assertStatusCode(2000, resp, content)
        self.assertContentType('application/json', resp, content)
        return resp, content

    # Tenant shortcuts

    def create_tenant(self, tenant_name):
        resp, content = create_tenant_json(tenant_name)
        self.assertStatusCode(201, resp, content)
        self.assertContentType('application/json', resp, content)
        return json.loads(content)['tenant']['id']
