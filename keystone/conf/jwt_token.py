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


valid_algorithms = cfg.StrOpt(
    'valid_algorithms',
    default='RS256,RS512,HS256,HS512',
    help=utils.fmt("""
List of valid JWT algorithms for tokens
"""))


verify_signature = cfg.BoolOpt(
    'verify_signature',
    default=True,
    help=utils.fmt("""
Toggle for enable JWT signature verification.
The signature will be verified against public key
(see verify_signature_public_key_path) or secret (see verify_signature_secret)
"""))

verify_signature_secret = cfg.StrOpt(
    'verify_signature_secret',
    help=utils.fmt("""
Secret for HS* JWT signature algorithms.
Used during verification of JWT tokens signature in jwt_token
authorization mechanism.
"""))

verify_signature_public_key_path = cfg.StrOpt(
    'verify_signature_public_key_path',
    help=utils.fmt("""
Path for public key for RS* JWT algorithms.
Used during verification of JWT tokens signature in jwt_token
authorization mechanism.
Destination file must be im PEM format.
"""))


verify_issuer = cfg.BoolOpt(
    'verify_issuer',
    default=True,
    help=utils.fmt("""
Toggle for enable JWT token verification against valid issuer names.
See verify_issuer_valid_issuers.
"""))

verify_issuer_valid_issuers = cfg.StrOpt(
    'verify_issuer_valid_issuers',
    help=utils.fmt("""
Valid names for JWT iss claim.
Used during verification of JWT tokens in jwt_token authorization mechanism.
Multiple names should be delimited by commas.
"""))


leeway = cfg.IntOpt(
    'leeway',
    min=0,
    default=30,
    help=utils.fmt("""
Number of seconds for time window for expiration check.
"""))


GROUP_NAME = __name__.split('.')[-1]
ALL_OPTS = [
    valid_algorithms,
    verify_signature,
    verify_signature_secret,
    verify_signature_public_key_path,

    verify_issuer,
    verify_issuer_valid_issuers,

    leeway,
]


def register_opts(conf):
    conf.register_opts(ALL_OPTS, group=GROUP_NAME)


def list_opts():
    return {GROUP_NAME: ALL_OPTS}
