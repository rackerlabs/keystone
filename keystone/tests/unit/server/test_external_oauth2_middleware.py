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
from unittest import mock

from keystonemiddleware import external_oauth2_token
import webtest

from keystone.common import context
from keystone.server.flask.request_processing.middleware import external_auth
from keystone.tests import unit


class TestExternalOAuth2Context(unit.TestCase):
    
    def setUp(self):
        super().setUp()
        
    def _create_simple_app(self):
        """Create a simple WSGI app for testing."""
        def simple_app(environ, start_response):
            body = b'Hello World'
            status = '200 OK'
            headers = [('Content-type', 'text/plain')]
            start_response(status, headers)
            return [body]
        return simple_app
        
    @mock.patch.object(external_oauth2_token.ExternalAuth2Protocol, '__init__', return_value=None)
    def test_external_oauth2_context_initialization(self, mock_parent_init):
        """Test that ExternalOAuth2Context initializes correctly."""
        app = self._create_simple_app()
        middleware = external_auth.ExternalOAuth2Context(app)
        
        # Verify parent __init__ was called with correct parameters
        mock_parent_init.assert_called_once_with(app, {})
        
        # Verify it is an instance of the correct class
        self.assertIsInstance(
            middleware, 
            external_auth.ExternalOAuth2Context
        )
        
    @mock.patch.object(external_oauth2_token.ExternalAuth2Protocol, '__init__', return_value=None)
    @mock.patch.object(external_oauth2_token.ExternalAuth2Protocol, 'process_request')
    def test_process_request_with_response_from_parent(self, mock_parent_process, mock_parent_init):
        """Test process_request when parent returns a response."""
        app = self._create_simple_app()
        middleware = external_auth.ExternalOAuth2Context(app)
        
        # Mock parent to return a response
        mock_response = mock.Mock()
        mock_parent_process.return_value = mock_response
        
        # Create mock request
        mock_request = mock.Mock()
        mock_request.environ = {}
        
        result = middleware.process_request(mock_request)
        
        # Should return the parent's response
        self.assertEqual(result, mock_response)
        mock_parent_process.assert_called_once_with(mock_request)
        
    @mock.patch.object(external_oauth2_token.ExternalAuth2Protocol, '__init__', return_value=None)
    @mock.patch.object(external_oauth2_token.ExternalAuth2Protocol, 'process_request')
    @mock.patch.object(context.RequestContext, 'from_environ')
    def test_process_request_without_parent_response(self, mock_from_environ, mock_parent_process, mock_parent_init):
        """Test process_request when parent doesn't return a response."""
        app = self._create_simple_app()
        middleware = external_auth.ExternalOAuth2Context(app)
        
        # Mock parent to return None (no response)
        mock_parent_process.return_value = None
        
        # Create mock request and context
        mock_request = mock.Mock()
        mock_request.environ = {'test': 'value'}
        mock_context = mock.Mock()
        mock_from_environ.return_value = mock_context
        
        result = middleware.process_request(mock_request)
        
        # Should return None (no response)
        self.assertIsNone(result)
        
        # Verify context creation and environment setting
        mock_from_environ.assert_called_once_with(
            mock_request.environ, 
            authenticated=True, 
            overwrite=True
        )
        self.assertEqual(
            mock_request.environ[context.REQUEST_CONTEXT_ENV], 
            mock_context
        )
        
    @mock.patch.object(external_oauth2_token.ExternalAuth2Protocol, '__init__', return_value=None)
    @mock.patch.object(external_oauth2_token.ExternalAuth2Protocol, 'process_request')
    def test_process_request_exception_handling(self, mock_parent_process, mock_parent_init):
        """Test that exceptions from parent process_request are propagated."""
        app = self._create_simple_app()
        middleware = external_auth.ExternalOAuth2Context(app)
        
        # Mock parent to raise an exception
        mock_parent_process.side_effect = Exception("Test exception")
        
        # Create mock request
        mock_request = mock.Mock()
        mock_request.environ = {}
        
        # Test that the exception is raised
        self.assertRaises(Exception, middleware.process_request, mock_request)
        
    @mock.patch.object(external_oauth2_token.ExternalAuth2Protocol, '__init__', return_value=None)
    def test_middleware_integration(self, mock_parent_init):
        """Test the middleware with a real WSGI application."""
        app = self._create_simple_app()
        middleware = external_auth.ExternalOAuth2Context(app)
        
        # The middleware should be created successfully
        self.assertIsInstance(
            middleware, 
            external_auth.ExternalOAuth2Context
        )
        
        # Verify parent initialization was called
        mock_parent_init.assert_called_once_with(app, {}) 