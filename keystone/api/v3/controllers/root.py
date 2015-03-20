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
import pecan

from keystone.api.common import controller
from keystone import assignment
from keystone import auth
from keystone import catalog
from keystone.contrib.ec2 import routers as ec2_routers
from keystone.contrib.endpoint_filter import routers as endpoint_filter_routers
from keystone.contrib.endpoint_policy import routers as endpoint_policy_routers
from keystone.contrib.federation import routers as federation_routers
from keystone.contrib.oauth1 import routers as oauth_routers
from keystone.contrib.revoke import routers as revoke_routers
from keystone.contrib import s3
from keystone.contrib.simple_cert import routers as simple_cert_routers
from keystone import credential
from keystone import identity
from keystone import policy
from keystone import resource
from keystone import trust

CONF = cfg.CONF
JSON_HOME = 'application/json-home'


__all__ = ['RootController']


class RootController(controller.PecanRoutesController):

    def get_routers(self, mapper):
        sub_routers = []
        self._routers = []

        modules = [
            assignment,
            auth,
            catalog,
            credential,
            identity,
            policy,
            resource
        ]

        if CONF.trust.enabled:
            modules.append(trust)

        for module in modules:
            routers_instance = module.routers.Routers()
            self._routers.append(routers_instance)
            routers_instance.append_v3_routers(mapper, sub_routers)

        return sub_routers

    def get_json_home_data(self, extensions=False):
        resources = dict()
        routers = self._routers

        if extensions:
            # FIXME(jamielennox): This is horrible, however the only way to
            # do json home listing with the current extension model. Fix
            # this as controllers and extensions are moved over to pecan.
            routers = self._routers + [
                ec2_routers.Ec2ExtensionV3(None, None),
                endpoint_filter_routers.EndpointFilterExtension(None, None),
                endpoint_policy_routers.EndpointPolicyExtension(None, None),
                federation_routers.FederationExtension(None, None),
                oauth_routers.OAuth1Extension(None, None),
                revoke_routers.RevokeExtension(None, None),
                s3.S3Extension(None, None),
                simple_cert_routers.SimpleCertExtension(None, None),
            ]

        for router in routers:
            resources.update(router.get_json_home_data())

        return {'resources': resources}

    @classmethod
    def data(cls, endpoint_type='public'):
        return {
            'id': 'v3.4',
            'status': 'stable',
            'updated': '2015-03-30T00:00:00Z',
            'links': [
                {
                    'rel': 'self',
                    'href': cls.get_identity_url(endpoint_type, 'v3'),
                }
            ],
            'media-types': [
                {
                    'base': 'application/json',
                    'type': controller.MEDIA_TYPE_JSON % 'v3'
                }
            ]
        }

    @controller.expose
    @pecan.expose('keystone:%s' % controller.JSON_HOME, controller.JSON_HOME)
    def index(self):
        accept = pecan.request.accept.best_match([controller.JSON,
                                                  controller.JSON_HOME])

        if accept == controller.JSON_HOME:
            pecan.response.content_type = controller.JSON_HOME
            return self.get_json_home_data()
        else:
            pecan.override_template('keystone:application/json',
                                    content_type='application/json')
            return {'version': self.data()}
