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

from keystone.conf import constants

from oslo_config import cfg


GROUP_NAME = __name__.split('.')[-1]
ALL_OPTS = [
    cfg.ListOpt('methods', default=constants._DEFAULT_AUTH_METHODS,
                help='Allowed authentication methods.'),
    cfg.StrOpt('password',  # nosec : This is the name of the plugin, not
               # a password that needs to be protected.
               help='Entrypoint for the password auth plugin module in '
                    'the keystone.auth.password namespace.'),
    cfg.StrOpt('token',
               help='Entrypoint for the token auth plugin module in the '
                    'keystone.auth.token namespace.'),
    # deals with REMOTE_USER authentication
    cfg.StrOpt('external',
               help='Entrypoint for the external (REMOTE_USER) auth '
                    'plugin module in the keystone.auth.external '
                    'namespace. Supplied drivers are DefaultDomain and '
                    'Domain. The default driver is DefaultDomain.'),
    cfg.StrOpt('oauth1',
               help='Entrypoint for the oAuth1.0 auth plugin module in '
                    'the keystone.auth.oauth1 namespace.'),
]


def _register_auth_plugin_opt(conf, option):
    conf.register_opt(option, group=GROUP_NAME)


def setup_authentication(conf):
    """Register non-default auth methods (used by extensions, etc)."""
    for method_name in conf.auth.methods:
        if method_name not in constants._DEFAULT_AUTH_METHODS:
            option = cfg.StrOpt(method_name)
            _register_auth_plugin_opt(conf, option)


def register_opts(conf):
    conf.register_opts(ALL_OPTS, group=GROUP_NAME)

    setup_authentication(conf)


def list_opts():
    return {GROUP_NAME: ALL_OPTS}
