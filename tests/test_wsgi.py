# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC
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

from babel import localedata
import gettext

from keystone import test

from keystone.common import wsgi
from keystone import exception
from keystone.openstack.common import gettextutils
from keystone.openstack.common import jsonutils


class FakeApp(wsgi.Application):
    def index(self, context):
        return {'a': 'b'}


class BaseWSGITest(test.TestCase):
    def setUp(self):
        self.app = FakeApp()
        super(BaseWSGITest, self).setUp()

    def _make_request(self, url='/'):
        req = wsgi.Request.blank(url)
        args = {'action': 'index', 'controller': None}
        req.environ['wsgiorg.routing_args'] = [None, args]
        return req

    def test_mask_password(self):
        message = ("test = 'password': 'aaaaaa', 'param1': 'value1', "
                   "\"new_password\": 'bbbbbb'")
        self.assertEqual(wsgi.mask_password(message, True),
                         u"test = 'password': '***', 'param1': 'value1', "
                         "\"new_password\": '***'")

        message = "test = 'password'  :   'aaaaaa'"
        self.assertEqual(wsgi.mask_password(message, False, '111'),
                         "test = 'password'  :   '111'")

        message = u"test = u'password' : u'aaaaaa'"
        self.assertEqual(wsgi.mask_password(message, True),
                         u"test = u'password' : u'***'")

        message = 'test = "password" : "aaaaaaaaa"'
        self.assertEqual(wsgi.mask_password(message),
                         'test = "password" : "***"')

        message = 'test = "original_password" : "aaaaaaaaa"'
        self.assertEqual(wsgi.mask_password(message),
                         'test = "original_password" : "***"')

        message = 'test = "original_password" : ""'
        self.assertEqual(wsgi.mask_password(message),
                         'test = "original_password" : "***"')

        message = 'test = "param1" : "value"'
        self.assertEqual(wsgi.mask_password(message),
                         'test = "param1" : "value"')


class ApplicationTest(BaseWSGITest):
    def test_response_content_type(self):
        req = self._make_request()
        resp = req.get_response(self.app)
        self.assertEqual(resp.content_type, 'application/json')

    def test_query_string_available(self):
        class FakeApp(wsgi.Application):
            def index(self, context):
                return context['query_string']
        req = self._make_request(url='/?1=2')
        resp = req.get_response(FakeApp())
        self.assertEqual(jsonutils.loads(resp.body), {'1': '2'})

    def test_headers_available(self):
        class FakeApp(wsgi.Application):
            def index(self, context):
                return context['headers']

        app = FakeApp()
        req = self._make_request(url='/?1=2')
        req.headers['X-Foo'] = "bar"
        resp = req.get_response(app)
        self.assertIn('X-Foo', eval(resp.body))

    def test_render_response(self):
        data = {'attribute': 'value'}
        body = '{"attribute": "value"}'

        resp = wsgi.render_response(body=data)
        self.assertEqual(resp.status, '200 OK')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.body, body)
        self.assertEqual(resp.headers.get('Vary'), 'X-Auth-Token')
        self.assertEqual(resp.headers.get('Content-Length'), str(len(body)))

    def test_render_response_custom_status(self):
        resp = wsgi.render_response(status=(501, 'Not Implemented'))
        self.assertEqual(resp.status, '501 Not Implemented')
        self.assertEqual(resp.status_int, 501)

    def test_render_response_custom_headers(self):
        resp = wsgi.render_response(headers=[('Custom-Header', 'Some-Value')])
        self.assertEqual(resp.headers.get('Custom-Header'), 'Some-Value')
        self.assertEqual(resp.headers.get('Vary'), 'X-Auth-Token')

    def test_render_response_no_body(self):
        resp = wsgi.render_response()
        self.assertEqual(resp.status, '204 No Content')
        self.assertEqual(resp.status_int, 204)
        self.assertEqual(resp.body, '')
        self.assertEqual(resp.headers.get('Content-Length'), '0')
        self.assertEqual(resp.headers.get('Content-Type'), None)

    def test_application_local_config(self):
        class FakeApp(wsgi.Application):
            def __init__(self, *args, **kwargs):
                self.kwargs = kwargs

        app = FakeApp.factory({}, testkey="test")
        self.assertIn("testkey", app.kwargs)
        self.assertEquals("test", app.kwargs["testkey"])

    def test_render_exception(self):
        e = exception.Unauthorized(message=u'\u7f51\u7edc')
        resp = wsgi.render_exception(e)
        self.assertEqual(resp.status_int, 401)


class ExtensionRouterTest(BaseWSGITest):
    def test_extensionrouter_local_config(self):
        class FakeRouter(wsgi.ExtensionRouter):
            def __init__(self, *args, **kwargs):
                self.kwargs = kwargs

        factory = FakeRouter.factory({}, testkey="test")
        app = factory(self.app)
        self.assertIn("testkey", app.kwargs)
        self.assertEquals("test", app.kwargs["testkey"])


class MiddlewareTest(BaseWSGITest):
    def test_middleware_request(self):
        class FakeMiddleware(wsgi.Middleware):
            def process_request(self, req):
                req.environ['fake_request'] = True
                return req
        req = self._make_request()
        resp = FakeMiddleware(None)(req)
        self.assertIn('fake_request', resp.environ)

    def test_middleware_response(self):
        class FakeMiddleware(wsgi.Middleware):
            def process_response(self, request, response):
                response.environ = {}
                response.environ['fake_response'] = True
                return response
        req = self._make_request()
        resp = FakeMiddleware(self.app)(req)
        self.assertIn('fake_response', resp.environ)

    def test_middleware_bad_request(self):
        class FakeMiddleware(wsgi.Middleware):
            def process_response(self, request, response):
                raise exception.Unauthorized()

        req = self._make_request()
        req.environ['REMOTE_ADDR'] = '127.0.0.1'
        resp = FakeMiddleware(self.app)(req)
        self.assertEquals(resp.status_int, exception.Unauthorized.code)

    def test_middleware_type_error(self):
        class FakeMiddleware(wsgi.Middleware):
            def process_response(self, request, response):
                raise TypeError()

        req = self._make_request()
        req.environ['REMOTE_ADDR'] = '127.0.0.1'
        resp = FakeMiddleware(self.app)(req)
        # This is a validationerror type
        self.assertEquals(resp.status_int, exception.ValidationError.code)

    def test_middleware_exception_error(self):
        class FakeMiddleware(wsgi.Middleware):
            def process_response(self, request, response):
                raise exception.UnexpectedError("EXCEPTIONERROR")

        req = self._make_request()
        resp = FakeMiddleware(self.app)(req)
        self.assertEquals(resp.status_int, exception.UnexpectedError.code)
        self.assertIn("EXCEPTIONERROR", resp.body)

    def test_middleware_local_config(self):
        class FakeMiddleware(wsgi.Middleware):
            def __init__(self, *args, **kwargs):
                self.kwargs = kwargs

        factory = FakeMiddleware.factory({}, testkey="test")
        app = factory(self.app)
        self.assertIn("testkey", app.kwargs)
        self.assertEquals("test", app.kwargs["testkey"])


class LocalizedResponseTest(test.TestCase):
    def setUp(self):
        super(LocalizedResponseTest, self).setUp()
        wsgi._AVAILABLE_LANGUAGES = []

    def tearDown(self):
        wsgi._AVAILABLE_LANGUAGES = []
        super(LocalizedResponseTest, self).tearDown()

    class TestMessage(gettextutils.Message):
        def __unicode__(self):
            return 'locale is %s' % self.locale

    def set_expected_languages(self, all_locales=[], avail_locales=None):
        # Override localedata.locale_identifiers to return some locales.
        def returns_some_locales(*args, **kwargs):
            return all_locales

        self.stubs.Set(localedata, 'locale_identifiers', returns_some_locales)

        # Override gettext.find to return other than None for some languages.
        def fake_gettext_find(*args, **kwargs):
            if avail_locales is None:
                # All locales are availale.
                return True
            languages = kwargs.get('languages')
            return (languages[0] in avail_locales) or None

        self.stubs.Set(gettext, 'find', fake_gettext_find)

    def test_get_languages_no_languages(self):
        # en_US is there if no languages available.
        self.assertEquals(wsgi.get_available_languages(), ['en_US'])

    def test_get_languages_other_languages(self):
        # Other languages are there if available and found, else not there.

        self.set_expected_languages(all_locales=['it', 'ha_NG'],
                                    avail_locales=['it'])

        self.assertEquals(set(wsgi.get_available_languages()),
                          set(['en_US', 'it']))

    def test_request_match_default(self):
        # The default language if no Accept-Language is provided is en_US
        req = wsgi.Request.blank('/')
        self.assertEquals(req.best_match_language(), 'en_US')

    def test_request_match_language_expected(self):
        # If Accept-Language is a supported language, best_match_language()
        # returns it.

        self.set_expected_languages(all_locales=['it'])

        req = wsgi.Request.blank('/', headers={'Accept-Language': 'it'})
        self.assertEquals(req.best_match_language(), 'it')

    def test_request_match_language_unexpected(self):
        # If Accept-Language is a language we do not support,
        # best_match_language() returns the default.

        self.set_expected_languages(all_locales=['it'])

        req = wsgi.Request.blank('/', headers={'Accept-Language': 'zh'})
        self.assertEquals(req.best_match_language(), 'en_US')

    def test_get_localized_Message_locale(self):
        # If the message is a gettextutils.Message, and locale provided,
        # the locale is set on the message and it's unicoded.

        msg = self.TestMessage(msg='something', domain='keystone')
        res = wsgi.get_localized_message(locale='test1', message=msg)

        self.assertEqual(res, 'locale is test1')

    def test_get_localized_Message_no_locale(self):
        # If the message is a gettextutils.Message, and locale not provided,
        # the locale is not set on the message and it's unicoded.

        msg = self.TestMessage(msg='something', domain='keystone')
        res = wsgi.get_localized_message(locale=None, message=msg)

        self.assertEqual(res, 'locale is None')

    def test_get_localized_not_Message(self):
        # If the message is not a gettextutils.Message, it's just unicoded.
        res = wsgi.get_localized_message(locale='test1', message='something')
        self.assertEqual(res, unicode('something'))

    def test_localized_message(self):
        # If the accept-language header is set on the request, the localized
        # message is returned by calling get_localized_message.

        self.set_expected_languages(all_locales=['it'])

        def fake_get_localized_message(locale, message):
            if (locale == 'it' and
                    message == "The resource could not be found."):
                return "Impossibile trovare la risorsa."

        self.stubs.Set(wsgi, 'get_localized_message',
                       fake_get_localized_message)

        text = 'The resource could not be found.'
        error = exception.NotFound(message=text)
        request = wsgi.Request.blank('/', headers={'Accept-Language': 'it'})
        resp = wsgi.render_exception(error, request=request)
        self.assertIn("Impossibile trovare la risorsa.", resp.body)
