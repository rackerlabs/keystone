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
    cfg.StrOpt('certfile',
               default=constants._CERTFILE,
               deprecated_for_removal=True,
               deprecated_reason=constants._DEPRECATE_PKI_MSG,
               help='Path of the certfile for token signing. For '
                    'non-production environments, you may be interested '
                    'in using `keystone-manage pki_setup` to generate '
                    'self-signed certificates.'),
    cfg.StrOpt('keyfile',
               default=constants._KEYFILE,
               deprecated_for_removal=True,
               deprecated_reason=constants._DEPRECATE_PKI_MSG,
               help='Path of the keyfile for token signing.'),
    cfg.StrOpt('ca_certs',
               deprecated_for_removal=True,
               deprecated_reason=constants._DEPRECATE_PKI_MSG,
               default='/etc/keystone/ssl/certs/ca.pem',
               help='Path of the CA for token signing.'),
    cfg.StrOpt('ca_key',
               default='/etc/keystone/ssl/private/cakey.pem',
               deprecated_for_removal=True,
               deprecated_reason=constants._DEPRECATE_PKI_MSG,
               help='Path of the CA key for token signing.'),
    cfg.IntOpt('key_size', default=2048, min=1024,
               deprecated_for_removal=True,
               deprecated_reason=constants._DEPRECATE_PKI_MSG,
               help='Key size (in bits) for token signing cert '
                    '(auto generated certificate).'),
    cfg.IntOpt('valid_days', default=3650,
               deprecated_for_removal=True,
               deprecated_reason=constants._DEPRECATE_PKI_MSG,
               help='Days the token signing cert is valid for '
                    '(auto generated certificate).'),
    cfg.StrOpt('cert_subject',
               deprecated_for_removal=True,
               deprecated_reason=constants._DEPRECATE_PKI_MSG,
               default=('/C=US/ST=Unset/L=Unset/O=Unset/'
                        'CN=www.example.com'),
               help='Certificate subject (auto generated certificate) for '
                    'token signing.'),
]


def register_opts(conf):
    conf.register_opts(ALL_OPTS, group=GROUP_NAME)


def list_opts():
    return {GROUP_NAME: ALL_OPTS}
