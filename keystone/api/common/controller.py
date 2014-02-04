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

import abc

import pecan
import routes
import six
import webob

from keystone.common import wsgi
from keystone import config

CONF = config.CONF

MEDIA_TYPE_JSON = 'application/vnd.openstack.identity-%s+json'
MEDIA_TYPE_XML = 'application/vnd.openstack.identity-%s+xml'


def expose(f):
    """Expose the common content types with the JSON renderer.

    This is the equivalent of doing a pecan.expose() on the method, however it
    exposes it across a range of content types and in a way that it works
    correctly with our existing XML middleware and such.
    """
    for content_type in ['application/json',
                         'application/xml',
                         'text/xml',
                         'text/html']:  # text/html is default if none given
        # the template in use here is a custom one that uses the oslo json
        # renderer so that everything produces the same output.
        template_f = pecan.expose(template='keystone:%s' % content_type,
                                  content_type=content_type,
                                  generic=False)
        f = template_f(f)

    return f


@six.add_metaclass(abc.ABCMeta)
class PecanRoutesController(object):

    def __init__(self):
        mapper = routes.Mapper()
        routers = self.get_routers(mapper)
        self._router = wsgi.ComposingRouter(mapper, routers)

    def get_routers(self, mapper):
        return []

    @staticmethod
    def get_identity_url(endpoint_type, version):
        """Returns a URL to keystone's own endpoint."""
        url = CONF['%s_endpoint' % endpoint_type] % CONF
        if url[-1] != '/':
            url += '/'
        return '%s%s/' % (url, version)

    @expose
    def _default(self, *remainder):
        results = self._router.map.routematch(environ=pecan.request.environ)

        if results:
            # NOTE(jamielennox): this appears to violate the
            # wsgiorg.routing_args standard but is consistent with routes
            match, route = results
            url = routes.util.URLGenerator(self._router.map,
                                           pecan.request.environ)
            pecan.request.environ['wsgiorg.routing_args'] = ((url), match)
            pecan.request.environ['routes.route'] = route
            pecan.request.environ['routes.url'] = url

            resp = match['controller'](pecan.request)
        else:
            raise webob.exc.HTTPNotFound()

        if isinstance(resp, webob.Response):
            # NOTE(jamielennox): Copy a webob response from old framework into
            # the pecan response. You have to return the actual pecan response
            # object to return webob directly from pecan.
            for attr in ['status', 'body', 'headers']:
                setattr(pecan.response, attr, getattr(resp, attr))
            return pecan.response

        return resp
