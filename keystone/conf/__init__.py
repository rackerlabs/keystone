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

from keystone.conf import assignment
from keystone.conf import auth
from keystone.conf import base
from keystone.conf import catalog
from keystone.conf import credential
from keystone.conf import domain_config
from keystone.conf import endpoint_filter
from keystone.conf import endpoint_policy
from keystone.conf import eventlet_server
from keystone.conf import federation
from keystone.conf import fernet_tokens
from keystone.conf import identity
from keystone.conf import identity_mapping
from keystone.conf import kvs
from keystone.conf import ldap
from keystone.conf import memcache
from keystone.conf import oauth1
from keystone.conf import os_inherit
from keystone.conf import paste_deploy
from keystone.conf import policy
from keystone.conf import resource
from keystone.conf import revoke
from keystone.conf import role
from keystone.conf import saml
from keystone.conf import shadow_users
from keystone.conf import signing
from keystone.conf import token
from keystone.conf import tokenless_auth
from keystone.conf import trust

CONF = cfg.CONF


conf_modules = [
    assignment,
    auth,
    base,
    catalog,
    credential,
    domain_config,
    endpoint_filter,
    endpoint_policy,
    eventlet_server,
    federation,
    fernet_tokens,
    identity,
    identity_mapping,
    kvs,
    ldap,
    memcache,
    oauth1,
    os_inherit,
    paste_deploy,
    policy,
    resource,
    revoke,
    role,
    saml,
    shadow_users,
    signing,
    token,
    tokenless_auth,
    trust,
]

for module in conf_modules:
    module.register_opts(CONF)
