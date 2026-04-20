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
Entry point for the IP allowlist backend driver in the
`keystone.ip_allowlist` namespace. Keystone only provides a `sql` driver, so
there is no reason to set this option unless you are providing a custom entry
point.
"""
    ),
)

enabled = cfg.BoolOpt(
    'enabled',
    default=False,
    help=utils.fmt(
        """
When enabled, Keystone will check the source IP address of every token
creation request against the per-user CIDR allowlist stored in the backend. If
a user has no CIDR entries the check is skipped (allow-all). If entries exist,
the source IP must match at least one CIDR or the request is rejected.
"""
    ),
)

client_ip_header = cfg.StrOpt(
    'client_ip_header',
    default=None,
    help=utils.fmt(
        """
Name of the HTTP header from which to read the client IP address when checking
the allowlist (e.g. `X-Forwarded-For` or `X-Real-IP`). If set, the leftmost
comma-separated value of the header is used. If the header is missing or
empty, Keystone falls back to the transport-level source IP
(`REMOTE_ADDR`). If unset, `REMOTE_ADDR` is used directly.

WARNING: when this option is set, the edge proxy MUST overwrite (or strip and
re-set) this header on incoming requests. Otherwise a client can spoof its IP
by sending the header itself and bypass the allowlist.
"""
    ),
)


GROUP_NAME = __name__.split('.')[-1]
ALL_OPTS = [driver, enabled, client_ip_header]


def register_opts(conf):
    conf.register_opts(ALL_OPTS, group=GROUP_NAME)


def list_opts():
    return {GROUP_NAME: ALL_OPTS}
