# Copyright 2016 Red Hat, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


from oslo_config import cfg

from tempest import config  # noqa


identity_group = cfg.OptGroup(name='identity',
                              title="Keystone Configuration Options")

IdentityGroup = [
    cfg.StrOpt('catalog_type',
               default='identity',
               help="Catalog type of the Identity service."),
    cfg.BoolOpt('disable_ssl_certificate_validation',
                default=False,
                help="Set to True if using self-signed SSL certificates."),
    cfg.StrOpt('ca_certificates_file',
               default=None,
               help='Specify a CA bundle file to use in verifying a '
                    'TLS (https) server certificate.'),
    cfg.StrOpt('uri',
               help="Full URI of the OpenStack Identity API (Keystone), v2"),
    cfg.StrOpt('uri_v3',
               help='Full URI of the OpenStack Identity API (Keystone), v3'),
    cfg.StrOpt('auth_version',
               default='v3',
               help="Identity API version to be used for authentication "
                    "for API tests."),
    cfg.StrOpt('region',
               default='RegionOne',
               help="The identity region name to use. Also used as the other "
                    "services' region name unless they are set explicitly. "
                    "If no such region is found in the service catalog, the "
                    "first found one is used."),
    cfg.StrOpt('v2_admin_endpoint_type',
               default='adminURL',
               choices=['public', 'admin', 'internal',
                        'publicURL', 'adminURL', 'internalURL'],
               help="The admin endpoint type to use for OpenStack Identity "
                    "(Keystone) API v2"),
    cfg.StrOpt('v2_public_endpoint_type',
               default='publicURL',
               choices=['public', 'admin', 'internal',
                        'publicURL', 'adminURL', 'internalURL'],
               help="The public endpoint type to use for OpenStack Identity "
                    "(Keystone) API v2",
               deprecated_opts=[cfg.DeprecatedOpt('endpoint_type',
                                                  group='identity')]),
    cfg.StrOpt('v3_endpoint_type',
               default='adminURL',
               choices=['public', 'admin', 'internal',
                        'publicURL', 'adminURL', 'internalURL'],
               help="The endpoint type to use for OpenStack Identity "
                    "(Keystone) API v3"),
    cfg.StrOpt('admin_role',
               default='admin',
               help="Role required to administrate keystone."),
    cfg.StrOpt('password',
               help="API key to use when authenticating.",
               secret=True,
               deprecated_for_removal=True),
    cfg.StrOpt('domain_name',
               help="Domain name for authentication (Keystone V3)."
                    "The same domain applies to user and project",
               deprecated_for_removal=True),
    cfg.StrOpt('alt_username',
               help="Username of alternate user to use for Nova API "
                    "requests.",
               deprecated_for_removal=True),
    cfg.StrOpt('alt_tenant_name',
               help="Alternate user's Tenant name to use for Nova API "
                    "requests.",
               deprecated_for_removal=True),
    cfg.StrOpt('alt_password',
               help="API key to use when authenticating as alternate user.",
               secret=True,
               deprecated_for_removal=True),
    cfg.StrOpt('alt_domain_name',
               help="Alternate domain name for authentication (Keystone V3)."
                    "The same domain applies to user and project",
               deprecated_for_removal=True),
    cfg.StrOpt('default_domain_id',
               default='default',
               help="ID of the default domain"),
]

identity_feature_group = cfg.OptGroup(name='identity-feature-enabled',
                                      title='Enabled Identity Features')

IdentityFeatureGroup = [
    cfg.BoolOpt('trust',
                default=True,
                help='Does the identity service have delegation and '
                     'impersonation enabled'),
    cfg.BoolOpt('api_v2',
                default=True,
                help='Is the v2 identity API enabled'),
    cfg.BoolOpt('api_v3',
                default=True,
                help='Is the v3 identity API enabled'),
    cfg.ListOpt('api_extensions',
                default=['all'],
                help="A list of enabled identity extensions with a special "
                     "entry all which indicates every extension is enabled. "
                     "Empty list indicates all extensions are disabled. "
                     "To get the list of extensions run: 'keystone discover'")
]
