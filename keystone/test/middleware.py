"""
Contans classes and stub WSGI apps for middleware testing
"""
from webob import Response, Request
from keystone.test import common


class HeaderApp(object):
    """
    Dummy WSGI app the returns HTTP headers in the body

    This is useful for making sure the headers we want
    aer being passwed down to the downstream WSGI app.
    """
    def __init__(self):
        pass

    def __call__(self, env, start_response):
        self.request = Request.blank('', environ=env)
        body = ''
        for key in env:
            if key.startswith('HTTP_'):
                body += '%s: %s\n' % (key, env[key])
        return Response(status="200 OK",
                        body=body)(env, start_response)


class BlankApp(object):
    """
    Dummy WSGI app - does not do anything
    """
    def __init__(self):
        pass

    def __call__(self, env, start_response):
        self.request = Request.blank('', environ=env)
        return Response(status="200 OK",
                        body={})(env, start_response)


class MiddlewareTestCase(common.FunctionalTestCase):
    """
    Base class to run tests for Keystone WSGI middleware.
    """
    use_server = True

    def setUp(self, middleware, settings=None):
        super(MiddlewareTestCase, self).setUp()
        if settings is None:
            settings = {'delay_auth_decision': '0',
                'auth_host': '127.0.0.1',
                'auth_port': '35357',
                'auth_protocol': 'http',
                'auth_uri': 'http://localhost:35357/',
                'admin_token': self.admin_token,
                'auth_admin_user': self.admin_username,
                'auth_admin_password': self.admin_password}
        cert_file = common.isSsl()
        if cert_file:
            settings['auth_protocol'] = 'https'
            settings['certfile'] = cert_file
            settings['auth_uri'] = 'https://localhost:35357/'
        if isinstance(middleware, tuple):
            self.test_middleware = HeaderApp()
            for filter in middleware:
                self.test_middleware = \
                filter.filter_factory(settings)(self.test_middleware)
        else:
            self.test_middleware = \
                middleware.filter_factory(settings)(HeaderApp())

        name = common.unique_str()
        r = self.create_tenant(tenant_name=name, assert_status=201)
        self.tenant = r.json.get('tenant')

        user_name = common.unique_str()
        password = common.unique_str()
        r = self.create_user(user_name=user_name,
                                     user_password=password,
                                     tenant_id=self.tenant['id'])
        self.tenant_user = r.json.get('user')
        self.tenant_user['password'] = password

        access = self.authenticate(user_name, password).\
            json['access']
        self.tenant_user_token = access['token']

        self.services = {}
        self.endpoint_templates = {}
        for x in range(0, 5):
            self.services[x] = self.create_service().json['OS-KSADM:service']
            self.endpoint_templates[x] = self.create_endpoint_template(
                name=self.services[x]['name'], \
                type=self.services[x]['type']).\
                json['OS-KSCATALOG:endpointTemplate']
            self.create_endpoint_for_tenant(self.tenant['id'],
                self.endpoint_templates[x]['id'])

    def test_401_without_token(self):
        resp = Request.blank('/').get_response(self.test_middleware)
        self.assertEquals(resp.status_int, 401)
        headers = resp.headers
        self.assertTrue("WWW-Authenticate" in headers)
        if common.isSsl():
            self.assertEquals(headers['WWW-Authenticate'],
                                    "Keystone uri='https://localhost:35357/'")
        else:
            self.assertEquals(headers['WWW-Authenticate'],
                                    "Keystone uri='http://localhost:35357/'")

    def test_401_bad_token(self):
        resp = Request.blank('/',
            headers={'X-Auth-Token': 'MADE_THIS_UP'}) \
            .get_response(self.test_middleware)
        self.assertEquals(resp.status_int, 401)

    def test_200_good_token(self):
        resp = Request.blank('/',
            headers={'X-Auth-Token': self.tenant_user_token['id']}) \
            .get_response(self.test_middleware)

        self.assertEquals(resp.status_int, 200)

        headers = resp.body.split('\n')

        header = "HTTP_X_IDENTITY_STATUS: Confirmed"
        self.assertTrue(header in headers, "Missing %s" % header)

        header = "HTTP_X_USER_ID: %s" % self.tenant_user['id']
        self.assertTrue(header in headers, "Missing %s" % header)

        header = "HTTP_X_USER_NAME: %s" % self.tenant_user['name']
        self.assertTrue(header in headers, "Missing %s" % header)

        header = "HTTP_X_TENANT_ID: %s" % self.tenant['id']
        self.assertTrue(header in headers, "Missing %s" % header)

        header = "HTTP_X_TENANT_NAME: %s" % self.tenant['name']
        self.assertTrue(header in headers, "Missing %s" % header)

        # These are here for legacy support and should be removed by F
        header = "HTTP_X_TENANT: %s" % self.tenant['id']
        self.assertTrue(header in headers, "Missing %s" % header)

        header = "HTTP_X_USER: %s" % self.tenant_user['id']
        self.assertTrue(header in headers, "Missing %s" % header)