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

from oslo_log import log as logging

import microversion_parse
from pycadf import cadftaxonomy as taxonomy
from pycadf import host
from pycadf import resource
import webob
from webob.descriptors import environ_getter

from keystone.common import api_version_request as api_version
from keystone.common import authorization
from keystone.common import context
from keystone.common import utils
import keystone.conf
from keystone import exception
from keystone.i18n import _


# Environment variable used to pass the request context
CONTEXT_ENV = 'openstack.context'

CONF = keystone.conf.CONF
LOG = logging.getLogger(__name__)

# Name of header used by clients to request a specific version
# of the REST API
API_VERSION_REQUEST_HEADER = 'X-OpenStack-API-Version'


class Request(webob.Request):

    _context_dict = None

    def __init__(self, *args, **kwargs):
        super(Request, self).__init__(*args, **kwargs)
        if not hasattr(self, 'api_version_request'):
            self.api_version_request = api_version.APIVersionRequest()

    def _get_context_dict(self):
        # allow middleware up the stack to provide context, params and headers.
        context = self.environ.get(CONTEXT_ENV, {})

        # NOTE(jamielennox): The webob package throws UnicodeError when a
        # param cannot be decoded. If we make webob iterate them now we can
        # catch this and throw an error early rather than on access.
        try:
            self.params.items()
        except UnicodeDecodeError:
            msg = _('Query string is not UTF-8 encoded')
            raise exception.ValidationError(msg)

        context['path'] = self.environ['PATH_INFO']
        scheme = self.environ.get(CONF.secure_proxy_ssl_header)
        if scheme:
            # NOTE(andrey-mp): "wsgi.url_scheme" contains the protocol used
            # before the proxy removed it ('https' usually). So if
            # the webob.Request instance is modified in order to use this
            # scheme instead of the one defined by API, the call to
            # webob.Request.relative_url() will return a URL with the correct
            # scheme.
            self.environ['wsgi.url_scheme'] = scheme
        context['host_url'] = self.host_url
        # authentication and authorization attributes are set as environment
        # values by the container and processed by the pipeline. The complete
        # set is not yet known.
        context['environment'] = self.environ

        if self.context:
            context['is_admin_project'] = self.context.is_admin_project

        context.setdefault('is_admin', False)
        return context

    @property
    def context_dict(self):
        if not self._context_dict:
            self._context_dict = self._get_context_dict()

        return self._context_dict

    @property
    def auth_context(self):
        return self.environ.get(authorization.AUTH_CONTEXT_ENV, {})

    def assert_authenticated(self):
        """Ensure that the current request has been authenticated."""
        if not self.context:
            msg = _('An authenticated call was made and there is '
                    'no request.context. This means the '
                    'auth_context middleware is not in place. You '
                    'must have this middleware in your pipeline '
                    'to perform authenticated calls')
            LOG.warning(msg)
            raise exception.Unauthorized(msg)

        if not self.context.authenticated:
            # auth_context didn't decode anything we can use
            raise exception.Unauthorized(
                _('auth_context did not decode anything useful'))

    @property
    def audit_initiator(self):
        """A pyCADF initiator describing the current authenticated context."""
        pycadf_host = host.Host(address=self.remote_addr,
                                agent=self.user_agent)
        initiator = resource.Resource(typeURI=taxonomy.ACCOUNT_USER,
                                      host=pycadf_host)

        if self.context.user_id:
            initiator.id = utils.resource_uuid(self.context.user_id)
            initiator.user_id = self.context.user_id

        if self.context.project_id:
            initiator.project_id = self.context.project_id

        if self.context.domain_id:
            initiator.domain_id = self.context.domain_id

        return initiator

    def set_api_version_request(self):
        """Set API version request based on the request header information."""
        hdr_string = microversion_parse.get_version(
            self.headers, service_type='identity',
            legacy_headers=[API_VERSION_REQUEST_HEADER])

        if hdr_string is None:
            self.api_version_request = api_version.APIVersionRequest(
                api_version.DEFAULT_API_VERSION)
        elif hdr_string == 'latest':
            # 'latest' is a special keyword which is equivalent to
            # requesting the maximum version of the API supported
            self.api_version_request = api_version.max_api_version()
        else:
            self.api_version_request = api_version.APIVersionRequest(
                hdr_string)

            # Check that the version requested is within the global
            # minimum/maximum of supported API versions
            if not self.api_version_request.matches(
                    api_version.min_api_version(),
                    api_version.max_api_version()):
                raise exception.InvalidGlobalAPIVersion(
                    req_ver=self.api_version_request.get_string(),
                    min_ver=api_version.min_api_version().get_string(),
                    max_ver=api_version.max_api_version().get_string())

    auth_type = environ_getter('AUTH_TYPE', None)
    remote_domain = environ_getter('REMOTE_DOMAIN', None)
    context = environ_getter(context.REQUEST_CONTEXT_ENV, None)
    token_auth = environ_getter('keystone.token_auth', None)
