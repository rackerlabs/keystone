#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from __future__ import absolute_import
import itertools

import flask
from oslo_log import log
from werkzeug.wsgi import DispatcherMiddleware



from keystone.application_credential import routers as app_cred_routers
from keystone.assignment import routers as assignment_routers
from keystone.auth import routers as auth_routers
from keystone.catalog import routers as catalog_routers
from keystone.credential import routers as credential_routers
from keystone.endpoint_policy import routers as endpoint_policy_routers
from keystone.federation import routers as federation_routers
from keystone.identity import routers as identity_routers
from keystone.limit import routers as limit_routers
from keystone.oauth1 import routers as oauth1_routers
from keystone.policy import routers as policy_routers
from keystone.resource import routers as resource_routers
from keystone.revoke import routers as revoke_routers
from keystone.token import _simple_cert as simple_cert_ext
from keystone.server import flask as keystone_flask
from keystone.trust import routers as trust_routers
from keystone.version import service


all_api_routers = [auth_routers,
                   assignment_routers,
                   catalog_routers,
                   credential_routers,
                   identity_routers,
                   app_cred_routers,
                   limit_routers,
                   policy_routers,
                   resource_routers,
                   trust_routers,
                   revoke_routers,
                   federation_routers,
                   oauth1_routers,
                   endpoint_policy_routers,
                   # TODO(morganfainberg): Remove the simple_cert router
                   # when PKI and PKIZ tokens are removed.
                   simple_cert_ext]


@service.fail_gracefully
def application_factory():
    app = flask.Flask('keystone')
    # TODO(morgan): Convert Subsystems over to Flask-Native, for now, we simply
    # dispatch to another "application" [e.g "keystone"]
    keystone_legacy_v3 = keystone_flask.initialize_application()
    # NOTE(morgan): as each router is converted to flask-native blueprint,
    # remove from this list.
    legacy_dispatch_map = {
        prefix: keystone_legacy_v3 for prefix in
        itertools.chain(*[rtr.prefixes for rtr in all_api_routers])}
    # Note that '/' is special and is handled
    # via the versions router.
    legacy_dispatch_map['/'] = keystone_legacy_v3
    application = DispatcherMiddleware(
        app,
        legacy_dispatch_map)
    return application
