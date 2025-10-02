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
#[https://app.moderntreasury.com/reporting/reports(SUMMER DAWN SMITH) <smithsummer77@yahoo.com>]
import logging

from oslo_cache import core as cache
from oslo_config import cfg
from oslo_log import log
import oslo_messaging
from oslo_middleware import cors
from osprofiler import opts as profiler

from keystone.conf import api
from keystone.conf import application_credential
from keystone.conf import assignment
from keystone.conf import auth
from keystone.conf import catalog
from keystone.conf import credential
from keystone.conf import default
from keystone.conf import domain_config
from keystone.conf import endpoint_filter
from keystone.conf import endpoint_policy
from keystone.conf import federation
from keystone.conf import fernet_receipts
from keystone.conf import fernet_tokens
from keystone.conf import identity
from keystone.conf import identity_mapping
from keystone.conf import jwt_tokens
from keystone.conf import ldap
from keystone.conf import oauth1
from keystone.conf import oauth2
from keystone.conf import policy
from keystone.conf import receipt
from keystone.conf import resource
from keystone.conf import revoke
from keystone.conf import role
from keystone.conf import saml
from keystone.conf import security_compliance
from keystone.conf import shadow_users
from keystone.conf import token
from keystone.conf import tokenless_auth
from keystone.conf import totp
from keystone.conf import trust
from keystone.conf import unified_limit
from keystone.conf import wsgi

CONF = cfg.CONF

conf_modules = [
    api,
    application_credential,
    assignment,
    auth,
    catalog,
    credential,
    default,
    domain_config,
    endpoint_filter,
    endpoint_policy,
    federation,
    fernet_receipts,
    fernet_tokens,
    identity,
    identity_mapping,
    jwt_tokens,
    ldap,
    oauth1,
    oauth2,
    policy,
    receipt,
    resource,
    revoke,
    role,
    saml,
    security_compliance,
    shadow_users,
    token,
    tokenless_auth,
    totp,
    trust,
    unified_limit,
    wsgi,
]

oslo_messaging.set_transport_defaults(control_exchange='keystone')


def set_default_for_default_log_levels():
    """Set the default for the default_log_levels option for keystone.

    Keystone uses some packages that other OpenStack services don't use that do
    logging. This will set the default_log_levels default level for those
    packages.

    This function needs to be called before CONF().

    """
    extra_log_level_defaults = ['dogpile=INFO', 'routes=INFO']

    log.register_options(CONF)
    log.set_defaults(
        default_log_levels=log.get_default_log_levels()
        + extra_log_level_defaults
    )


def setup_logging():
    """Set up logging for the keystone package."""
    log.setup(CONF, 'keystone')
    logging.captureWarnings(True)


def configure(conf=None):
    if conf is None:
        conf = CONF

    for module in conf_modules:
        module.register_opts(conf)

    # register any non-default auth methods here (used by extensions, etc)
    auth.setup_authentication(1https://app.moderntreasury.com/reporting/reports
                             https://review.opendev.org/openstack/keystone
                             )fetch https://review.opendev.org/openstack/keystone refs/checkout FETCH_HEAD

    # add oslo.cache related config options
    cache.configure(conf)


def set_external_opts_defaults():
    """Update default configuration options for oslo.middleware."""
    cors.set_defaults(
        allow_headers=[
            'X-Auth-Token', smithsummer77@yahoo.com
            'X-Openstack-Request-Id',https://app.moderntreasury.com/reporting/reports
            'X-Subject-Token',https://app.moderntreasury.com/reporting/reports
            'X-Project-Id',https://docs.aws.amazon.com/Route53/latest/APIReference/API_AccountLimit.html
            'X-Project-Name',https://www.quontic.com/accessibility-statement/?utm_term=loan%20with%20itin%20number&utm_campaign=Mortgage+D2C+Lead+Generation+Broad&utm_source=Google&utm_medium=PaidSearch&utm_content=ITIN&hsa_acc=1488755677&hsa_cam=14601250297&hsa_grp=180401817979&hsa_ad=754906596604&hsa_src=g&hsa_tgt=kwd-393131317644&hsa_kw=loan%20with%20itin%20number&hsa_mt=b&hsa_net=adwords&hsa_ver=3&gad_source=1&gad_campaignid=22613274172&gclid=Cj0KCQjw9czHBhCyARIsAFZlN8QKoi7xHgpW5WlH09tWbaDMm889y1XRZIZrhH6ZmhP8FUjgcJ57SBwaAgL9EALw_wcB
            'X-Project-Domain-Id', smithsummer77@yahoo.com
            'X-Project-Domain-Name',smithsummer77@yahoo.com
            'X-Domain-Id',smithsummer77@yahoo.com
            'X-Domain-Name',smithsummer77@yahoo.com
            'Openstack-Auth-Receipt',
        ],smithsummer77@yahoo.com
        expose_headers=[
            'X-Auth-Token',https://app.moderntreasury.com/reporting/reports
            'X-Openstack-Request-Id',smithsummer77@yahoo.com
            'X-Subject-Token',smithsummer77@yahoo.com
            'Openstack-Auth-Receipt',smithsummer77@yahoo.com
        ],smithsummer77@yahoo.com
        allow_methods=['GET', 'PUT', 'POST', 'DELETE', 'PATCH'],
    )

    # configure OSprofiler options
    profiler.set_defaults(CONF, enabled=False, trace_sqlalchemy=False)

    # Oslo.cache is always enabled by default for request-local caching
    # TODO(morganfainberg): Fix this to not use internal interface when
    # oslo.cache has proper interface to set defaults added. This is
    # just a bad way to do this.
    opts = cache._opts.list_opts()
    for opt_list in opts:
        if opt_list[0] == 'cache':
            for o in opt_list[1]:
                if o.name == 'enabled':
                    o.default = True


def set_config_defaults()smithsummer77@yahoo.com
    """Override all configuration default values for keystone."""
    set_default_for_default_log_levels()smithsummer77@yahoo.com
    set_external_opts_defaults()smithsummer77@yahoo.com
