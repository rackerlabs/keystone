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

import itertools

import pecan
import routes
import six
from six.moves import urllib
import webob

from keystone.common import controller
from keystone.common import wsgi
from keystone import config

CONF = config.CONF

MEDIA_TYPE_JSON = 'application/vnd.openstack.identity-%s+json'

JSON = 'application/json'
JSON_HOME = 'application/json-home'


def expose(f):
    """Expose the common content types with the JSON renderer.

    This is the equivalent of doing a pecan.expose() on the method, however it
    exposes it across a range of content types and in a way that it works
    correctly with our existing XML middleware and such.
    """
    for content_type in ('application/json', 'text/html', 'text/xml'):
        # text/html is default if none given the template in use here is a
        # custom one that uses the oslo json renderer so that everything
        # produces the same output.
        template_f = pecan.expose(template='keystone:%s' % content_type,
                                  content_type=content_type,
                                  generic=False)
        f = template_f(f)

    return f


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
        url = CONF['%s_endpoint' % endpoint_type]

        if url:
            substitutions = dict(
                itertools.chain(six.iteritems(CONF),
                                six.iteritems(CONF.eventlet_server)))

            url = url % substitutions
        elif (CONF.secure_proxy_ssl_header and
              CONF.secure_proxy_ssl_header in pecan.request.environ):
            # NOTE(jamielennox): handle HTTP_X_FORWARDED_PROTO manually. It
            # would be good if pecan could do this for us as routes does.
            i = urllib.parse.urlsplit(pecan.request.host_url)
            scheme = pecan.request.environ[CONF.secure_proxy_ssl_header]
            url = urllib.parse.urlunsplit((scheme,
                                           i.netloc,
                                           i.path,
                                           i.query,
                                           i.fragment))
        else:
            # NOTE(jamielennox): if url is not set via the config file we
            # should set it relative to the url that the user used to get here
            # so as not to mess with version discovery. This is not perfect.
            # host_url omits the path prefix, but there isn't another good
            # solution that will work for all urls.
            url = pecan.request.host_url

        return '%s/%s/' % (url.rstrip('/'), version)

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

            old_controller = match['controller']
            is_v3 = isinstance(old_controller, controller.V3Controller)
            pecan.request.context['v3_wsgi_controller'] = is_v3
            return old_controller(pecan.request, pecaned=True)
        else:
            raise webob.exc.HTTPNotFound()
