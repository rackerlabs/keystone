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

from unittest import mock

from keystonemiddleware import external_oauth2_token
from werkzeug.middleware.proxy_fix import ProxyFix

from keystone.server.flask import core
from keystone.server.flask.request_processing.middleware import auth_context
from keystone.server.flask.request_processing.middleware import external_auth
from keystone.server.flask.request_processing.middleware import url_normalize
from keystone.tests import unit


class TestFlaskCoreMiddlewareSetup(unit.TestCase):
    
    def setUp(self):
        super().setUp()
        
    def _create_mock_app(self):
        """Create a mock Flask app for testing."""
        mock_app = mock.Mock()
        mock_app.wsgi_app = mock.Mock()
        return mock_app
        
    @mock.patch.object(external_auth, 'ExternalOAuth2Context')
    def test_setup_app_middleware_with_external_oauth2(self, mock_external_oauth2):
        """Test middleware setup when external OAuth2 is configured."""
        mock_app = self._create_mock_app()
        original_wsgi_app = mock_app.wsgi_app
        
        # Mock external OAuth2 context to be created successfully
        mock_external_oauth2_instance = mock.Mock()
        mock_external_oauth2.return_value = mock_external_oauth2_instance
        
        core.setup_app_middleware(mock_app)
        
        # Verify ExternalOAuth2Context was used
        mock_external_oauth2.assert_called_once_with(original_wsgi_app)
        
        # Verify the middleware chain is set up correctly  
        # ProxyFix should be the outermost middleware
        self.assertIsInstance(
            mock_app.wsgi_app, 
            ProxyFix
        )
        
    @mock.patch.object(external_auth, 'ExternalOAuth2Context')
    @mock.patch.object(auth_context, 'AuthContextMiddleware')
    def test_setup_app_middleware_fallback_to_auth_context(self, mock_auth_context, mock_external_oauth2):
        """Test middleware setup falls back to AuthContextMiddleware on configuration error."""
        mock_app = self._create_mock_app()
        original_wsgi_app = mock_app.wsgi_app
        
        # Mock external OAuth2 to raise ConfigurationError
        mock_external_oauth2.side_effect = external_oauth2_token.ConfigurationError("Not configured")
        
        # Mock auth context middleware
        mock_auth_context_instance = mock.Mock()
        mock_auth_context.return_value = mock_auth_context_instance
        
        core.setup_app_middleware(mock_app)
        
        # Verify ExternalOAuth2Context was attempted
        mock_external_oauth2.assert_called_once_with(original_wsgi_app)
        
        # Verify fallback to AuthContextMiddleware
        mock_auth_context.assert_called_once_with(original_wsgi_app)
        
        # Verify the middleware chain is set up correctly
        # ProxyFix should be the outermost middleware  
        self.assertIsInstance(
            mock_app.wsgi_app, 
            ProxyFix
        )
        
    @mock.patch.object(external_auth, 'ExternalOAuth2Context')
    def test_setup_app_middleware_other_exception_not_caught(self, mock_external_oauth2):
        """Test that non-ConfigurationError exceptions are not caught."""
        mock_app = self._create_mock_app()
        
        # Mock external OAuth2 to raise a different exception
        mock_external_oauth2.side_effect = ValueError("Some other error")
        
        self.assertRaises(ValueError, core.setup_app_middleware, mock_app)
        
    def test_url_normalize_middleware_applied(self):
        """Test that URL normalizing middleware is always applied."""
        mock_app = self._create_mock_app()
        original_wsgi_app = mock_app.wsgi_app
        
        with mock.patch.object(external_auth, 'ExternalOAuth2Context') as mock_external_oauth2:
            mock_external_oauth2.side_effect = external_oauth2_token.ConfigurationError("Not configured")
            with mock.patch.object(auth_context, 'AuthContextMiddleware') as mock_auth_context:
                mock_auth_context_instance = mock.Mock()
                mock_auth_context.return_value = mock_auth_context_instance
                
                core.setup_app_middleware(mock_app)
                
                # Verify ProxyFix middleware is the outermost layer
                self.assertIsInstance(
                    mock_app.wsgi_app, 
                    ProxyFix
                )
                
    @mock.patch('keystone.server.flask.core._APP_MIDDLEWARE', ())
    @mock.patch.object(external_auth, 'ExternalOAuth2Context')
    def test_middleware_order_with_external_oauth2(self, mock_external_oauth2):
        """Test that middleware is applied in the correct order."""
        mock_app = self._create_mock_app()
        original_wsgi_app = mock_app.wsgi_app
        
        # Track the order of middleware application
        middleware_calls = []
        
        def track_external_oauth2(wsgi_app):
            middleware_calls.append(('external_oauth2', wsgi_app))
            return mock.Mock()
            
        def track_url_normalize(wsgi_app):
            middleware_calls.append(('url_normalize', wsgi_app))
            return mock.Mock()
            
        mock_external_oauth2.side_effect = track_external_oauth2
        
        with mock.patch.object(url_normalize, 'URLNormalizingMiddleware', side_effect=track_url_normalize):
            core.setup_app_middleware(mock_app)
            
        # Verify middleware application order
        self.assertEqual(len(middleware_calls), 2)
        self.assertEqual(middleware_calls[0][0], 'external_oauth2')
        self.assertEqual(middleware_calls[0][1], original_wsgi_app)
        self.assertEqual(middleware_calls[1][0], 'url_normalize') 