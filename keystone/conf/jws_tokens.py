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


key_repository = cfg.StrOpt(
    'key_repository',
    default='/etc/keystone/jws-keys/',
    help=utils.fmt("""
Directory containing JWS keys. This directory must exist before using
`keystone-manage jwt_setup` for the first time, must be writable by the user
running `keystone-manage jwt_setup`, and of course must be readable by
keystone's server process. It must contain at least one asymmetric key pair. It
can contain multiple public keys in order to validate tokens from keystone
servers in the same deployment. This option is only applicable in deployments
issuing JWS tokens and setting `keystone.conf [tokens] provider = jws`.
"""))
signing_key = cfg.StrOpt(
    'signing_key',
    default='/etc/keystone/jws-keys/private.pem',
    help=utils.fmt("""
A private asymmetric key used to sign JSON Web Tokens. The private key must be
usable with an Elliptic Curve Digital Signature Algorithm using SHA-256.
The key can be created out-of-band, or it can be generated using
`keystone-manage jwt_setup`. Note that `keystone-manage` will create ECDSA key
pairs using P-256, or SECP256R1, curves. Note that the keys used in this
repository should only be used for signing and verification. Their usage should
not be mixed with asymmetric encryption, even though the keys themselves may
support that use case.
"""))


GROUP_NAME = __name__.split('.')[-1]
ALL_OPTS = [
    key_repository,
]


def register_opts(conf):
    conf.register_opts(ALL_OPTS, group=GROUP_NAME)


def list_opts():
    return {GROUP_NAME: ALL_OPTS}
