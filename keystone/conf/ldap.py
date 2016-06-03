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


GROUP_NAME = __name__.split('.')[-1]
ALL_OPTS = [
    cfg.StrOpt('url', default='ldap://localhost',
               help='URL(s) for connecting to the LDAP server. Multiple '
                    'LDAP URLs may be specified as a comma separated '
                    'string. The first URL to successfully bind is used '
                    'for the connection.'),
    cfg.StrOpt('user',
               help='User BindDN to query the LDAP server.'),
    cfg.StrOpt('password', secret=True,
               help='Password for the BindDN to query the LDAP server.'),
    cfg.StrOpt('suffix', default='cn=example,cn=com',
               help='LDAP server suffix'),
    cfg.BoolOpt('use_dumb_member', default=False,
                help='If true, will add a dummy member to groups. This is '
                     'required if the objectclass for groups requires the '
                     '"member" attribute.'),
    cfg.StrOpt('dumb_member', default='cn=dumb,dc=nonexistent',
               help='DN of the "dummy member" to use when '
                    '"use_dumb_member" is enabled.'),
    cfg.BoolOpt('allow_subtree_delete', default=False,
                help='Delete subtrees using the subtree delete control. '
                     'Only enable this option if your LDAP server '
                     'supports subtree deletion.'),
    cfg.StrOpt('query_scope', default='one',
               choices=['one', 'sub'],
               help='The LDAP scope for queries, "one" represents '
                    'oneLevel/singleLevel and "sub" represents '
                    'subtree/wholeSubtree options.'),
    cfg.IntOpt('page_size', default=0,
               help='Maximum results per page; a value of zero ("0") '
                    'disables paging.'),
    cfg.StrOpt('alias_dereferencing', default='default',
               choices=['never', 'searching', 'always', 'finding',
                        'default'],
               help='The LDAP dereferencing option for queries. The '
                    '"default" option falls back to using default '
                    'dereferencing configured by your ldap.conf.'),
    cfg.IntOpt('debug_level',
               help='Sets the LDAP debugging level for LDAP calls. '
                    'A value of 0 means that debugging is not enabled. '
                    'This value is a bitmask, consult your LDAP '
                    'documentation for possible values.'),
    cfg.BoolOpt('chase_referrals',
                help='Override the system\'s default referral chasing '
                     'behavior for queries.'),
    cfg.StrOpt('user_tree_dn',
               help='Search base for users. '
                    'Defaults to the suffix value.'),
    cfg.StrOpt('user_filter',
               help='LDAP search filter for users.'),
    cfg.StrOpt('user_objectclass', default='inetOrgPerson',
               help='LDAP objectclass for users.'),
    cfg.StrOpt('user_id_attribute', default='cn',
               help='LDAP attribute mapped to user id. '
                    'WARNING: must not be a multivalued attribute.'),
    cfg.StrOpt('user_name_attribute', default='sn',
               help='LDAP attribute mapped to user name.'),
    cfg.StrOpt('user_description_attribute', default='description',
               help='LDAP attribute mapped to user description.'),
    cfg.StrOpt('user_mail_attribute', default='mail',
               help='LDAP attribute mapped to user email.'),
    cfg.StrOpt('user_pass_attribute', default='userPassword',
               help='LDAP attribute mapped to password.'),
    cfg.StrOpt('user_enabled_attribute', default='enabled',
               help='LDAP attribute mapped to user enabled flag.'),
    cfg.BoolOpt('user_enabled_invert', default=False,
                help='Invert the meaning of the boolean enabled values. '
                     'Some LDAP servers use a boolean lock attribute '
                     'where "true" means an account is disabled. Setting '
                     '"user_enabled_invert = true" will allow these lock '
                     'attributes to be used. This setting will have no '
                     'effect if "user_enabled_mask" or '
                     '"user_enabled_emulation" settings are in use.'),
    cfg.IntOpt('user_enabled_mask', default=0,
               help='Bitmask integer to indicate the bit that the enabled '
                    'value is stored in if the LDAP server represents '
                    '"enabled" as a bit on an integer rather than a '
                    'boolean. A value of "0" indicates the mask is not '
                    'used. If this is not set to "0" the typical value '
                    'is "2". This is typically used when '
                    '"user_enabled_attribute = userAccountControl".'),
    cfg.StrOpt('user_enabled_default', default='True',
               help='Default value to enable users. This should match an '
                    'appropriate int value if the LDAP server uses '
                    'non-boolean (bitmask) values to indicate if a user '
                    'is enabled or disabled. If this is not set to "True" '
                    'the typical value is "512". This is typically used '
                    'when "user_enabled_attribute = userAccountControl".'),
    cfg.ListOpt('user_attribute_ignore',
                default=['default_project_id'],
                help='List of attributes stripped off the user on '
                     'update.'),
    cfg.StrOpt('user_default_project_id_attribute',
               help='LDAP attribute mapped to default_project_id for '
                    'users.'),
    cfg.BoolOpt('user_allow_create', default=True,
                deprecated_for_removal=True,
                deprecated_reason="Write support for Identity LDAP "
                                  "backends has been deprecated in the M "
                                  "release and will be removed in the O "
                                  "release.",
                help='Allow user creation in LDAP backend.'),
    cfg.BoolOpt('user_allow_update', default=True,
                deprecated_for_removal=True,
                deprecated_reason="Write support for Identity LDAP "
                                  "backends has been deprecated in the M "
                                  "release and will be removed in the O "
                                  "release.",
                help='Allow user updates in LDAP backend.'),
    cfg.BoolOpt('user_allow_delete', default=True,
                deprecated_for_removal=True,
                deprecated_reason="Write support for Identity LDAP "
                                  "backends has been deprecated in the M "
                                  "release and will be removed in the O "
                                  "release.",
                help='Allow user deletion in LDAP backend.'),
    cfg.BoolOpt('user_enabled_emulation', default=False,
                help='If true, Keystone uses an alternative method to '
                     'determine if a user is enabled or not by checking '
                     'if they are a member of the '
                     '"user_enabled_emulation_dn" group.'),
    cfg.StrOpt('user_enabled_emulation_dn',
               help='DN of the group entry to hold enabled users when '
                    'using enabled emulation.'),
    cfg.BoolOpt('user_enabled_emulation_use_group_config', default=False,
                help='Use the "group_member_attribute" and '
                     '"group_objectclass" settings to determine '
                     'membership in the emulated enabled group.'),
    cfg.ListOpt('user_additional_attribute_mapping',
                default=[],
                help='List of additional LDAP attributes used for mapping '
                     'additional attribute mappings for users. Attribute '
                     'mapping format is <ldap_attr>:<user_attr>, where '
                     'ldap_attr is the attribute in the LDAP entry and '
                     'user_attr is the Identity API attribute.'),
    cfg.StrOpt('group_tree_dn',
               help='Search base for groups. '
                    'Defaults to the suffix value.'),
    cfg.StrOpt('group_filter',
               help='LDAP search filter for groups.'),
    cfg.StrOpt('group_objectclass', default='groupOfNames',
               help='LDAP objectclass for groups.'),
    cfg.StrOpt('group_id_attribute', default='cn',
               help='LDAP attribute mapped to group id.'),
    cfg.StrOpt('group_name_attribute', default='ou',
               help='LDAP attribute mapped to group name.'),
    cfg.StrOpt('group_member_attribute', default='member',
               help='LDAP attribute mapped to show group membership.'),
    cfg.StrOpt('group_desc_attribute', default='description',
               help='LDAP attribute mapped to group description.'),
    cfg.ListOpt('group_attribute_ignore', default=[],
                help='List of attributes stripped off the group on '
                     'update.'),
    cfg.BoolOpt('group_allow_create', default=True,
                deprecated_for_removal=True,
                deprecated_reason="Write support for Identity LDAP "
                                  "backends has been deprecated in the M "
                                  "release and will be removed in the O "
                                  "release.",
                help='Allow group creation in LDAP backend.'),
    cfg.BoolOpt('group_allow_update', default=True,
                deprecated_for_removal=True,
                deprecated_reason="Write support for Identity LDAP "
                                  "backends has been deprecated in the M "
                                  "release and will be removed in the O "
                                  "release.",
                help='Allow group update in LDAP backend.'),
    cfg.BoolOpt('group_allow_delete', default=True,
                deprecated_for_removal=True,
                deprecated_reason="Write support for Identity LDAP "
                                  "backends has been deprecated in the M "
                                  "release and will be removed in the O "
                                  "release.",
                help='Allow group deletion in LDAP backend.'),
    cfg.ListOpt('group_additional_attribute_mapping',
                default=[],
                help='Additional attribute mappings for groups. Attribute '
                     'mapping format is <ldap_attr>:<user_attr>, where '
                     'ldap_attr is the attribute in the LDAP entry and '
                     'user_attr is the Identity API attribute.'),

    cfg.StrOpt('tls_cacertfile',
               help='CA certificate file path for communicating with '
                    'LDAP servers.'),
    cfg.StrOpt('tls_cacertdir',
               help='CA certificate directory path for communicating with '
                    'LDAP servers.'),
    cfg.BoolOpt('use_tls', default=False,
                help='Enable TLS for communicating with LDAP servers.'),
    cfg.StrOpt('tls_req_cert', default='demand',
               choices=['demand', 'never', 'allow'],
               help='Specifies what checks to perform on client '
                    'certificates in an incoming TLS session.'),
    cfg.BoolOpt('use_pool', default=True,
                help='Enable LDAP connection pooling.'),
    cfg.IntOpt('pool_size', default=10,
               help='Connection pool size.'),
    cfg.IntOpt('pool_retry_max', default=3,
               help='Maximum count of reconnect trials.'),
    cfg.FloatOpt('pool_retry_delay', default=0.1,
                 help='Time span in seconds to wait between two '
                      'reconnect trials.'),
    cfg.IntOpt('pool_connection_timeout', default=-1,
               help='Connector timeout in seconds. Value -1 indicates '
                    'indefinite wait for response.'),
    cfg.IntOpt('pool_connection_lifetime', default=600,
               help='Connection lifetime in seconds.'),
    cfg.BoolOpt('use_auth_pool', default=True,
                help='Enable LDAP connection pooling for end user '
                     'authentication. If use_pool is disabled, then this '
                     'setting is meaningless and is not used at all.'),
    cfg.IntOpt('auth_pool_size', default=100,
               help='End user auth connection pool size.'),
    cfg.IntOpt('auth_pool_connection_lifetime', default=60,
               help='End user auth connection lifetime in seconds.'),
    cfg.BoolOpt('group_members_are_ids', default=False,
                help='If the members of the group objectclass are user '
                     'IDs rather than DNs, set this to true. This is the '
                     'case when using posixGroup as the group '
                     'objectclass and OpenDirectory.'),
]


def register_opts(conf):
    conf.register_opts(ALL_OPTS, group=GROUP_NAME)


def list_opts():
    return {GROUP_NAME: ALL_OPTS}
