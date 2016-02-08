# Copyright 2012 OpenStack Foundation
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

from oslo_config import cfg
from oslo_log import log
from oslo_log import versionutils

from keystone.common import wsgi
from keystone.i18n import _


CONF = cfg.CONF
LOG = log.getLogger(__name__)

# Header used to transmit the auth token
AUTH_TOKEN_HEADER = wsgi.AUTH_TOKEN_HEADER


# Header used to transmit the subject token
SUBJECT_TOKEN_HEADER = wsgi.SUBJECT_TOKEN_HEADER


# Environment variable used to pass the request context
CONTEXT_ENV = wsgi.CONTEXT_ENV


# Environment variable used to pass the request params
PARAMS_ENV = wsgi.PARAMS_ENV


class TokenAuthMiddleware(wsgi.Middleware):
    def __init__(self, application):
        super(TokenAuthMiddleware, self).__init__(application)
        msg = _("Remove token_auth from the paste file, the "
                "token_auth middleware is now built into the main "
                "request handler. Update the "
                "[pipeline:admin_api], and "
                "[pipeline:public_api] sections in keystone-paste.ini "
                "accordingly, as it will be removed in the O release.")
        versionutils.report_deprecated_feature(LOG, msg)


class AdminTokenAuthMiddleware(wsgi.Middleware):
    """A trivial filter that checks for a pre-defined admin token.

    Sets 'is_admin' to true in the context, expected to be checked by
    methods that are admin-only.

    """

    def __init__(self, application):
        super(AdminTokenAuthMiddleware, self).__init__(application)
        msg = _("Remove admin_token_auth from the paste-ini file, the "
                "admin_token_auth middleware has been deprecated in favor of "
                "using keystone-manage bootstrap and real users after "
                "bootstrap process. Update the [pipline:api_v3], "
                "[pipeline:api_admin], and [pipeline:api_public] sections "
                "accordingly, as it will be removed in the O release.")
        versionutils.report_deprecated_feature(LOG, msg)

    def process_request(self, request):
        token = request.headers.get(AUTH_TOKEN_HEADER)
        context = request.environ.get(CONTEXT_ENV, {})
        context['is_admin'] = (token == CONF.admin_token)
        request.environ[CONTEXT_ENV] = context


class PostParamsMiddleware(wsgi.Middleware):
    """Middleware to allow method arguments to be passed as POST parameters.

    Filters out the parameters `self`, `context` and anything beginning with
    an underscore.

    """

    def process_request(self, request):
        params_parsed = request.params
        params = {}
        for k, v in params_parsed.items():
            if k in ('self', 'context'):
                continue
            if k.startswith('_'):
                continue
            params[k] = v

        request.environ[PARAMS_ENV] = params


class JsonBodyMiddleware(wsgi.Middleware):
    def __init__(self, application):
        super(JsonBodyMiddleware, self).__init__(application)
        msg = _("Remove json_body from the paste file, the "
                "json_body middleware is now built into the main "
                "request handler. Update the "
                "[pipeline:admin_api], and "
                "[pipeline:public_api] sections in keystone-paste.ini "
                "accordingly, as it will be removed in the O release.")
        versionutils.report_deprecated_feature(LOG, msg)


class NormalizingFilter(wsgi.Middleware):
    """Middleware filter to handle URL normalization."""

    def process_request(self, request):
        """Normalizes URLs."""
        # Removes a trailing slash from the given path, if any.
        if (len(request.environ['PATH_INFO']) > 1 and
                request.environ['PATH_INFO'][-1] == '/'):
            request.environ['PATH_INFO'] = request.environ['PATH_INFO'][:-1]
        # Rewrites path to root if no path is given.
        elif not request.environ['PATH_INFO']:
            request.environ['PATH_INFO'] = '/'
