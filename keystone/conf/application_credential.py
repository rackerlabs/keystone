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

from keystone.conf import utils

driver = cfg.StrOpt(
    'driver',
    default='sql',
    help=utils.fmt(
        """
Entry point for the application credential backend driver in the
`keystone.application_credential` namespace.  Keystone only provides a `sql`
driver, so there is no reason to change this unless you are providing a custom
entry point.
"""
    ),
)

caching = cfg.BoolOpt(
    'caching',
    default=True,
    help=utils.fmt(
        """
Toggle for application credential caching. This has no effect unless global
caching is enabled.
"""
    ),
)

cache_time = cfg.IntOpt(
    'cache_time',
    help=utils.fmt(
        """
Time to cache application credential data in seconds. This has no effect
unless global caching is enabled.
"""
    ),
)

user_limit = cfg.IntOpt(
    'user_limit',
    default=-1,
    help=utils.fmt(
        """
Maximum number of application credentials a user is permitted to create. A
value of -1 means unlimited. If a limit is not set, users are permitted to
create application credentials at will, which could lead to bloat in the
keystone database or open keystone to a DoS attack.
"""
    ),
)


federated_enabled = cfg.BoolOpt(
    'federated_enabled',
    default=True,
    help=utils.fmt(
        """
Allow federated users to create application credentials. Set to ``False``
to prevent federated users from creating application credentials entirely.
When federation is configured, either this option must be set to ``False``
or ``federated_max_duration_days`` must be greater than zero; otherwise
application credentials for federated users are unlimited and may outlive
the upstream IdP session lifetime.
"""
    ),
)

federated_max_duration_days = cfg.IntOpt(
    'federated_max_duration_days',
    default=30,
    min=0,
    help=utils.fmt(
        """
Maximum lifetime in days for application credentials created by federated
users. A value of ``0`` means unlimited. The default of ``30`` days ensures
that federated application credentials expire before long-term IdP session
drift can occur. If ``expires_at`` is not provided at creation time, it is
automatically set to ``now + federated_max_duration_days``. If a requested
``expires_at`` exceeds this maximum it is rejected with HTTP 400.
"""
    ),
)

federated_allow_unrestricted = cfg.BoolOpt(
    'federated_allow_unrestricted',
    default=False,
    help=utils.fmt(
        """
Allow federated users to create unrestricted application credentials.
Unrestricted application credentials can themselves manage application
credentials and trusts, representing a significant privilege escalation
risk for credentials that may outlive the upstream IdP session. This
defaults to ``False`` to prevent federated users from creating
unrestricted application credentials.
"""
    ),
)

GROUP_NAME = __name__.split('.')[-1]
ALL_OPTS = [
    driver,
    caching,
    cache_time,
    user_limit,
    federated_enabled,
    federated_max_duration_days,
    federated_allow_unrestricted,
]


def register_opts(conf):
    conf.register_opts(ALL_OPTS, group=GROUP_NAME)


def list_opts():
    return {GROUP_NAME: ALL_OPTS}
