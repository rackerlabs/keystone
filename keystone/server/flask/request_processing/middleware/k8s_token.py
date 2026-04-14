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

"""Kubernetes token authentication middleware for Keystone federation.

Validates Kubernetes/OpenShift bearer tokens and populates the WSGI
environment with user identity claims for consumption by Keystone's
federation ``mapped`` auth plugin.

Supports two token types:

* **JWT service-account tokens** — validated locally via the cluster's
  JWKS endpoint (``/openid/v1/jwks``).  This is equivalent to what
  ``mod_auth_openidc`` does with ``AuthType oauth20``.

* **Opaque OAuth tokens** (``sha256~…``) — validated by calling the
  Kubernetes TokenReview API.  This covers OpenShift human-user tokens
  that ``mod_auth_openidc`` cannot handle.

After successful validation the middleware sets ``REMOTE_USER`` and
``HTTP_OIDC_*``-style environment variables so that the existing
federation mapping rules work without modification.

The middleware is activated only on paths that match a configurable
federation endpoint pattern (default:
``/v3/OS-FEDERATION/identity_providers/<idp>/protocols/k8s-token/auth``).
All other requests pass through untouched.

Configuration lives in ``[k8s_auth]`` section of ``keystone.conf``
and is entirely optional — when running on a pod the defaults are
derived from the mounted service-account credentials.
"""

import json
import os
import re
import ssl

from oslo_log import log
import urllib.error
import urllib.request

LOG = log.getLogger(__name__)

_SA_TOKEN_PATH = (
    '/var/run/secrets/kubernetes.io/serviceaccount/token'
)
_SA_CA_PATH = (
    '/var/run/secrets/kubernetes.io/serviceaccount/ca.crt'
)
_K8S_API = 'https://kubernetes.default.svc'

_DEFAULT_PATH_RE = re.compile(
    r'/v3/OS-FEDERATION/identity_providers/'
    r'[^/]+/protocols/k8s_token/auth$'
)

# Paths that trigger the OAuth2 authorization-code redirect flow
# (browser-based websso).
_WEBSSO_PATH_RE = re.compile(
    r'/v3/auth/OS-FEDERATION/'
    r'(?:identity_providers/[^/]+/protocols/k8s_token/websso'
    r'|websso/k8s_token)$'
)


class K8sTokenAuthMiddleware(object):
    """Validate Kubernetes bearer tokens for Keystone federation."""

    def __init__(self, app, k8s_api_url=None, ca_path=None,
                 verify_ssl=True, claim_prefix='OIDC-',
                 oauth_client_id=None, oauth_client_secret=None,
                 oauth_authorize_url=None, oauth_token_url=None):
        self.app = app
        self.k8s_api_url = k8s_api_url or _K8S_API
        self.ca_path = ca_path or _SA_CA_PATH
        self.verify_ssl = verify_ssl
        self.claim_prefix = claim_prefix
        self.oauth_client_id = oauth_client_id
        self.oauth_client_secret = oauth_client_secret
        self.oauth_authorize_url = oauth_authorize_url
        self.oauth_token_url = oauth_token_url
        self._jwks = None

    # ------------------------------------------------------------------
    # WSGI entry point
    # ------------------------------------------------------------------

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')

        if _DEFAULT_PATH_RE.search(path):
            return self._handle_bearer(environ, start_response)

        if _WEBSSO_PATH_RE.search(path):
            return self._handle_websso(environ, start_response)

        return self.app(environ, start_response)

    # ------------------------------------------------------------------
    # Bearer token validation (API path)
    # ------------------------------------------------------------------

    def _handle_bearer(self, environ, start_response):
        auth_header = environ.get('HTTP_AUTHORIZATION', '')
        if not auth_header.lower().startswith('bearer '):
            return self._unauthorized(
                start_response, 'Missing Bearer token')

        token = auth_header[7:]
        user_info = self._validate_token(token)
        if user_info is None:
            return self._unauthorized(
                start_response, 'Token validation failed')

        self._populate_environ(environ, user_info)
        return self.app(environ, start_response)

    # ------------------------------------------------------------------
    # WebSSO redirect flow (browser path)
    # ------------------------------------------------------------------

    def _handle_websso(self, environ, start_response):
        query = environ.get('QUERY_STRING', '')
        params = dict(
            p.split('=', 1) for p in query.split('&') if '=' in p
        )

        if 'code' in params:
            return self._handle_websso_callback(
                environ, start_response, params)

        return self._redirect_to_ocp_login(
            environ, start_response, params)

    def _redirect_to_ocp_login(self, environ, start_response,
                               params):
        if not self.oauth_authorize_url:
            return self._unauthorized(
                start_response,
                'OAuth authorize URL not configured')

        scheme = environ.get('wsgi.url_scheme', 'https')
        host = environ.get('HTTP_HOST', 'localhost')
        path = environ.get('PATH_INFO', '')
        redirect_uri = '%s://%s%s' % (scheme, host, path)

        origin = params.get('origin', '')

        url = (
            '%s?client_id=%s'
            '&response_type=code'
            '&redirect_uri=%s'
            '&scope=user%%3Ainfo'
            '&state=%s'
        ) % (
            self.oauth_authorize_url,
            self.oauth_client_id,
            urllib.request.quote(redirect_uri, safe=''),
            urllib.request.quote(origin, safe=''),
        )

        start_response(
            '302 Found', [('Location', url)])
        return [b'']

    def _handle_websso_callback(self, environ, start_response,
                                params):
        code = params['code']
        scheme = environ.get('wsgi.url_scheme', 'https')
        host = environ.get('HTTP_HOST', 'localhost')
        path = environ.get('PATH_INFO', '')
        redirect_uri = '%s://%s%s' % (scheme, host, path)

        token = self._exchange_code_for_token(
            code, redirect_uri)
        if token is None:
            return self._unauthorized(
                start_response,
                'OAuth code exchange failed')

        user_info = self._validate_token(token)
        if user_info is None:
            return self._unauthorized(
                start_response, 'Token validation failed')

        self._populate_environ(environ, user_info)

        origin = params.get('state', '')
        if origin:
            environ['QUERY_STRING'] = 'origin=%s' % origin

        return self.app(environ, start_response)

    def _exchange_code_for_token(self, code, redirect_uri):
        if not self.oauth_token_url:
            LOG.error('OAuth token URL not configured')
            return None

        data = (
            'grant_type=authorization_code'
            '&code=%s'
            '&redirect_uri=%s'
            '&client_id=%s'
            '&client_secret=%s'
        ) % (
            urllib.request.quote(code, safe=''),
            urllib.request.quote(redirect_uri, safe=''),
            urllib.request.quote(self.oauth_client_id, safe=''),
            urllib.request.quote(
                self.oauth_client_secret or '', safe=''),
        )

        req = urllib.request.Request(
            self.oauth_token_url,
            data=data.encode('utf-8'),
            headers={'Content-Type':
                     'application/x-www-form-urlencoded'},
            method='POST')

        try:
            ctx = self._ssl_context()
            resp = urllib.request.urlopen(req, context=ctx,
                                         timeout=10)
            body = json.loads(resp.read())
            return body.get('access_token')
        except (urllib.error.URLError, ValueError,
                KeyError) as e:
            LOG.error('OAuth token exchange failed: %s', e)
            return None

    # ------------------------------------------------------------------
    # Token validation
    # ------------------------------------------------------------------

    def _validate_token(self, token):
        """Validate a bearer token.

        Returns a dict with ``username``, ``uid``, ``groups`` on
        success, or ``None`` on failure.

        JWT tokens (starting with ``eyJ``) are validated locally
        against the cluster JWKS.  Opaque tokens (``sha256~…``) are
        validated via the TokenReview API.
        """
        if token.startswith('eyJ'):
            return self._validate_jwt(token)
        return self._validate_opaque(token)

    def _validate_jwt(self, token):
        """Validate a JWT service-account token via JWKS."""
        try:
            import jwt as pyjwt
        except ImportError:
            LOG.warning('PyJWT not installed; falling back to '
                        'TokenReview for JWT validation')
            return self._validate_opaque(token)

        try:
            jwks = self._get_jwks()
            public_keys = {}
            for key_data in jwks.get('keys', []):
                kid = key_data.get('kid')
                if kid:
                    public_keys[kid] = (
                        pyjwt.algorithms.RSAAlgorithm
                        .from_jwk(key_data))

            header = pyjwt.get_unverified_header(token)
            kid = header.get('kid')
            if kid not in public_keys:
                LOG.warning('JWT kid %s not in JWKS', kid)
                return None

            claims = pyjwt.decode(
                token,
                key=public_keys[kid],
                algorithms=['RS256'],
                options={'verify_aud': False})

            return {
                'username': claims.get('sub', ''),
                'uid': claims.get(
                    'kubernetes.io', {}).get(
                    'serviceaccount', {}).get(
                    'uid', ''),
                'groups': [],
                'extra': claims,
            }
        except pyjwt.exceptions.PyJWTError as e:
            LOG.warning('JWT validation failed: %s', e)
            return None

    def _validate_opaque(self, token):
        """Validate an opaque token via Kubernetes TokenReview."""
        sa_token = self._get_sa_token()
        if sa_token is None:
            LOG.error('No service account token available '
                      'for TokenReview')
            return None

        review = {
            'apiVersion': 'authentication.k8s.io/v1',
            'kind': 'TokenReview',
            'spec': {'token': token},
        }

        url = '%s/apis/authentication.k8s.io/v1/tokenreviews' % (
            self.k8s_api_url)
        req = urllib.request.Request(
            url,
            data=json.dumps(review).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'Bearer %s' % sa_token,
            },
            method='POST')

        try:
            ctx = self._ssl_context()
            resp = urllib.request.urlopen(req, context=ctx,
                                         timeout=10)
            body = json.loads(resp.read())
        except (urllib.error.URLError, ValueError) as e:
            LOG.error('TokenReview request failed: %s', e)
            return None

        status = body.get('status', {})
        if not status.get('authenticated'):
            LOG.warning('TokenReview: token not authenticated')
            return None

        user = status.get('user', {})
        return {
            'username': user.get('username', ''),
            'uid': user.get('uid', ''),
            'groups': user.get('groups', []),
            'extra': user.get('extra', {}),
        }

    # ------------------------------------------------------------------
    # Environ population
    # ------------------------------------------------------------------

    def _populate_environ(self, environ, user_info):
        """Set WSGI environ variables for Keystone federation.

        Mimics the variables that ``mod_auth_openidc`` would set,
        so existing federation mapping rules continue to work.
        """
        username = user_info['username']
        environ['REMOTE_USER'] = username

        # Build environ keys that match what Keystone's federation
        # assertion filter expects.  The assertion_prefix config
        # (``[federation] assertion_prefix``) tells Keystone which
        # environ keys to treat as identity claims.  We use the
        # same prefix here so the mapping rules can reference them
        # directly (e.g. ``HTTP_OIDC_SUB`` when prefix is
        # ``HTTP_OIDC_``).
        prefix = 'HTTP_%s' % self.claim_prefix.replace('-', '_')

        environ['%sSUB' % prefix] = username
        environ['%sISS' % prefix] = self.k8s_api_url
        environ['%sAUD' % prefix] = self.k8s_api_url

        groups = user_info.get('groups', [])
        if groups:
            environ['%sGROUPS' % prefix] = ';'.join(groups)

        if user_info.get('uid'):
            environ['%sUID' % prefix] = user_info['uid']

        extra = user_info.get('extra', {})
        if isinstance(extra, dict):
            for key, val in extra.items():
                env_key = '%s%s' % (
                    prefix,
                    key.upper().replace('.', '_')
                        .replace('/', '_')
                        .replace(':', '_'))
                if isinstance(val, (list, dict)):
                    environ[env_key] = json.dumps(val)
                else:
                    environ[env_key] = str(val)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_sa_token(self):
        """Read the pod's service-account token."""
        try:
            with open(_SA_TOKEN_PATH) as f:
                return f.read().strip()
        except (IOError, OSError):
            LOG.warning('Cannot read service account token '
                        'from %s', _SA_TOKEN_PATH)
            return os.environ.get('K8S_SA_TOKEN')

    def _get_jwks(self):
        """Fetch the cluster JWKS (cached)."""
        if self._jwks is not None:
            return self._jwks

        url = '%s/openid/v1/jwks' % self.k8s_api_url
        req = urllib.request.Request(url)
        try:
            ctx = self._ssl_context()
            resp = urllib.request.urlopen(req, context=ctx,
                                         timeout=10)
            self._jwks = json.loads(resp.read())
            return self._jwks
        except (urllib.error.URLError, ValueError) as e:
            LOG.error('Failed to fetch JWKS from %s: %s',
                      url, e)
            return {'keys': []}

    def _ssl_context(self):
        """Build an SSL context using the cluster CA."""
        ctx = ssl.create_default_context()
        if not self.verify_ssl:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        elif os.path.exists(self.ca_path):
            ctx.load_verify_locations(self.ca_path)
        return ctx

    @staticmethod
    def _unauthorized(start_response, message):
        start_response(
            '401 Unauthorized',
            [('Content-Type', 'application/json')])
        body = json.dumps({
            'error': {
                'message': message,
                'code': 401,
                'title': 'Unauthorized',
            }
        })
        return [body.encode('utf-8')]
