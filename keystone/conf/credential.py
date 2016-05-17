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
Entrypoint for the credential backend driver in the keystone.credential
namespace.
"""))

provider = cfg.StrOpt(
    'provider',
    default='fernet',
    help=utils.fmt("""
Controls the credential encryption and decryption operations. Entrypoint in
the keystone.credential.provider namespace. Core provider is [fernet].
"""))

encryption_keys = cfg.ListOpt(
    'encryption_keys',
    secret=True,
    default=[],
    help=utils.fmt("""
List of fernet keys used for credential encryption.  The first key is the
active key used for encryption and all fernet keys are used for decryption.
When this value is not set encryption is not used.
"""))

allow_plaintext = cfg.BoolOpt(
    'allow_plaintext',
    default=True,
    help=utils.fmt("""
Allow fields to not be encrypted when retrieving them from backend.  This
should be disabled once credentials have been encrypted using the
keystone-manage db_encrypt command.
"""))

GROUP_NAME = __name__.split('.')[-1]
ALL_OPTS = [
    driver,
    provider,
    encryption_keys,
    allow_plaintext
]


def register_opts(conf):
    conf.register_opts(ALL_OPTS, group=GROUP_NAME)


def list_opts():
    return {GROUP_NAME: ALL_OPTS}
