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
    help=utils.fmt("""
Entry point for the credential backend driver in the `keystone.credential`
namespace. Keystone only provides a `sql` driver, so there's no reason to
change this unless you are providing a custom entry point.
"""))

provider = cfg.StrOpt(
    'provider',
    default='fernet',
    help=utils.fmt("""
Controls the credential encryption and decryption operations. Entry point in
the ``keystone.credential.provider`` namespace. Default provider is [fernet].
"""))

encrypt = cfg.BoolOpt(
    'encrypt',
    default=False,
    help=utils.fmt("""
Encrypt credentials before storing them in the backend. Once enabled, newly
created or updated credentials will be encrypted before being persisted. To
manually migrate existing credentials, please use the ``keystone-manage
credential_migrate`` command.
"""))

key_repository = cfg.StrOpt(
    'key_repository',
    default='/etc/keystone/credential-keys/',
    help=utils.fmt("""
Directory containing Encrypted Credential keys.  Credential token keys have no
relationship to Fernet token keys.
"""))

max_active_keys = cfg.IntOpt(
    'max_active_keys',
    default=2,
    help=utils.fmt("""
This controls how many keys are held in rotation by keystone-manage
credential_rotate before they are discarded. The default value of 3 means that
keystone will maintain one staged key, one primary key, and one secondary key.
Increasing this value means that additional secondary keys will be kept in the
rotation.
"""))


GROUP_NAME = __name__.split('.')[-1]
ALL_OPTS = [
    driver,
    provider,
    encrypt,
    key_repository,
    max_active_keys
]


def register_opts(conf):
    conf.register_opts(ALL_OPTS, group=GROUP_NAME)


def list_opts():
    return {GROUP_NAME: ALL_OPTS}
