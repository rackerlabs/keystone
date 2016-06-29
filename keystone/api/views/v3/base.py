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

import copy
import itertools

from oslo_config import cfg

CONF = cfg.CONF


class View(object):

    required_params = None
    optional_params = None

    member_name = None
    collection_name = None

    include_extras = True

    def __init__(self, request):
        self.request = request

    @property
    def base_url(self):
        url = CONF.public_endpoint

        if url:
            substitutions = dict(itertools.chain(CONF.items(),
                                                 CONF.eventlet_server.items()))
            url = url % substitutions

        else:
            url = self.request.host_url

        return url.rstrip('/')

    @property
    def collection_url(self):
        return '/'.join([self.base_url,
                         'v3',
                         self.collection_name])

    def member_url(self, obj):
        return '%s/%s' % (self.collection_url, obj['id'])

    def render(self, obj):
        if self.include_extras:
            for p in self.required_params or []:
                if p not in obj:
                    # do something better here
                    raise RuntimeError()

            output = copy.deepcopy(obj)

        else:
            output = {}

            for p in self.required_params or []:
                try:
                    output[p] = obj[p]
                except KeyError:
                    # do something better here
                    raise RuntimeError()

            for p in self.optional_params or []:
                try:
                    output[p] = obj[p]
                except KeyError:
                    pass

        links = output.setdefault('links', {})
        links['self'] = self.member_url(obj)

        return output

    def show(self, obj):
        return {self.member_name: self.render(obj)}

    def list(self, objs, truncated=False):
        output = {
            self.collection_name: [self.render(o) for o in objs],
            'links': {'next': None,
                      'previous': None,
                      'self': self.collection_url}
        }

        if truncated:
            output['truncated'] = True

        return output
