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


identity_group = cfg.OptGroup(name='identity',
                              title="Keystone Configuration Options")

IdentityGroup = []

identity_feature_group = cfg.OptGroup(name='identity-feature-enabled',
                                      title='Enabled Identity Features')

IdentityFeatureGroup = []

scenario_group = cfg.OptGroup(name='scenario',
                              title='Scenario Test Options')

ScenarioGroup = [
    cfg.StrOpt('fed_idp_id',
               default='ipsilon',
               help='Identity Provider ID'),
    cfg.StrOpt('fed_protocol_id',
               default='saml2',
               help='Protocol ID'),
    cfg.StrOpt('fed_idp_ecp_url',
               default='https://ipa.rduartes.unknown.test/idp/saml2/SSO/SOAP',
               help='Identity Provider SAML2/ECP URL'),
    cfg.StrOpt('fed_idp_username',
               default='admin',
               help='Username used to login in the Identity Provider'),
    cfg.StrOpt('fed_idp_password',
               default='FreeIPA4All',
               help='Password used to login in the Identity Provider'),
]
