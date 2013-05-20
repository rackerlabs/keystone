# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC
#
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

import gettext
import os
import sys

from oslo.config import cfg

from keystone.common import logging
from keystone.openstack.common import log as logging

gettext.install('keystone', unicode=1)

_DEFAULT_LOG_FORMAT = "%(asctime)s %(levelname)8s [%(name)s] %(message)s"
_DEFAULT_LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_DEFAULT_AUTH_METHODS = ['password', 'token']


CONF = cfg.CONF


def setup_logging(conf, product_name='keystone'):
    """
    Sets up the logging options for a log with supplied name

    :param conf: a cfg.ConfOpts object
    :param product_name: project name required by
                         keystone.openstack.common.log
    """
    logging.setup(product_name)


def setup_authentication():
    # register any non-default auth methods here (used by extensions, etc)
    for method_name in CONF.auth.methods:
        if method_name not in _DEFAULT_AUTH_METHODS:
            register_str(method_name, group="auth")


def register_str(*args, **kw):
    conf = kw.pop('conf', CONF)
    group = kw.pop('group', None)
    return conf.register_opt(cfg.StrOpt(*args, **kw), group=group)


def register_cli_str(*args, **kw):
    conf = kw.pop('conf', CONF)
    group = kw.pop('group', None)
    return conf.register_cli_opt(cfg.StrOpt(*args, **kw), group=group)


def register_list(*args, **kw):
    conf = kw.pop('conf', CONF)
    group = kw.pop('group', None)
    return conf.register_opt(cfg.ListOpt(*args, **kw), group=group)


def register_cli_list(*args, **kw):
    conf = kw.pop('conf', CONF)
    group = kw.pop('group', None)
    return conf.register_cli_opt(cfg.ListOpt(*args, **kw), group=group)


def register_bool(*args, **kw):
    conf = kw.pop('conf', CONF)
    group = kw.pop('group', None)
    return conf.register_opt(cfg.BoolOpt(*args, **kw), group=group)


def register_cli_bool(*args, **kw):
    conf = kw.pop('conf', CONF)
    group = kw.pop('group', None)
    return conf.register_cli_opt(cfg.BoolOpt(*args, **kw), group=group)


def register_int(*args, **kw):
    conf = kw.pop('conf', CONF)
    group = kw.pop('group', None)
    return conf.register_opt(cfg.IntOpt(*args, **kw), group=group)


def register_cli_int(*args, **kw):
    conf = kw.pop('conf', CONF)
    group = kw.pop('group', None)
    return conf.register_cli_opt(cfg.IntOpt(*args, **kw), group=group)


def configure():
    #CONF.register_cli_opts(COMMON_CLI_OPTS)
    #CONF.register_cli_opts(LOGGING_CLI_OPTS)
    CONF.register_cli_opts(logging.common_cli_opts)
    CONF.register_cli_opts(logging.logging_cli_opts)

    register_cli_bool('standard-threads', default=False)

    register_cli_str('pydev-debug-host', default=None)
    register_cli_int('pydev-debug-port', default=None)

    register_str('admin_token', secret=True, default='ADMIN')
    register_str('bind_host', default='0.0.0.0')
    register_int('compute_port', default=8774)
    register_int('admin_port', default=35357)
    register_int('public_port', default=5000)
    register_str(
        'public_endpoint', default='http://localhost:%(public_port)s/')
    register_str('admin_endpoint', default='http://localhost:%(admin_port)s/')
    register_str('onready')
    register_str('auth_admin_prefix', default='')
    register_str('policy_file', default='policy.json')
    register_str('policy_default_rule', default=None)
    # default max request size is 112k
    register_int('max_request_body_size', default=114688)
    register_int('max_param_size', default=64)
    # we allow tokens to be a bit larger to accommodate PKI
    register_int('max_token_size', default=8192)
    register_str(
        'member_role_id', default='9fe2ff9ee4384b1894a90878d3e92bab')
    register_str('member_role_name', default='_member_')

    # identity
    register_str('default_domain_id', group='identity', default='default')

    # trust
    register_bool('enabled', group='trust', default=True)

    # ssl
    register_bool('enable', group='ssl', default=False)
    register_str('certfile', group='ssl',
                 default="/etc/keystone/ssl/certs/keystone.pem")
    register_str('keyfile', group='ssl',
                 default="/etc/keystone/ssl/private/keystonekey.pem")
    register_str('ca_certs', group='ssl',
                 default="/etc/keystone/ssl/certs/ca.pem")
    register_str('ca_key', group='ssl',
                 default="/etc/keystone/ssl/certs/cakey.pem")
    register_bool('cert_required', group='ssl', default=False)
    register_int('key_size', group='ssl', default=1024)
    register_int('valid_days', group='ssl', default=3650)
    register_str('ca_password', group='ssl', default=None)
    register_str('cert_subject', group='ssl',
                 default='/C=US/ST=Unset/L=Unset/O=Unset/CN=localhost')

    # signing
    register_str(
        'token_format', group='signing', default="PKI")
    register_str(
        'certfile',
        group='signing',
        default="/etc/keystone/ssl/certs/signing_cert.pem")
    register_str(
        'keyfile',
        group='signing',
        default="/etc/keystone/ssl/private/signing_key.pem")
    register_str(
        'ca_certs',
        group='signing',
        default="/etc/keystone/ssl/certs/ca.pem")
    register_str('ca_key', group='signing',
                 default="/etc/keystone/ssl/certs/cakey.pem")
    register_int('key_size', group='signing', default=1024)
    register_int('valid_days', group='signing', default=3650)
    register_str('ca_password', group='signing', default=None)
    register_str('cert_subject', group='signing',
                 default='/C=US/ST=Unset/L=Unset/O=Unset/CN=www.example.com')

    # sql
    register_str('connection', group='sql', secret=True,
                 default='sqlite:///keystone.db')
    register_int('idle_timeout', group='sql', default=200)

    register_str(
        'driver',
        group='catalog',
        default='keystone.catalog.backends.sql.Catalog')
    register_str(
        'driver',
        group='identity',
        default='keystone.identity.backends.sql.Identity')
    register_str(
        'driver',
        group='credential',
        default='keystone.credential.backends.sql.Credential')
    register_str(
        'driver',
        group='policy',
        default='keystone.policy.backends.sql.Policy')
    register_str(
        'driver', group='token', default='keystone.token.backends.kvs.Token')
    register_str(
        'driver', group='trust', default='keystone.trust.backends.sql.Trust')
    register_str(
        'driver', group='ec2', default='keystone.contrib.ec2.backends.kvs.Ec2')
    register_str(
        'driver',
        group='stats',
        default='keystone.contrib.stats.backends.kvs.Stats')

    # ldap
    register_str('url', group='ldap', default='ldap://localhost')
    register_str('user', group='ldap', default=None)
    register_str('password', group='ldap', secret=True, default=None)
    register_str('suffix', group='ldap', default='cn=example,cn=com')
    register_bool('use_dumb_member', group='ldap', default=False)
    register_str('dumb_member', group='ldap', default='cn=dumb,dc=nonexistent')
    register_bool('allow_subtree_delete', group='ldap', default=False)
    register_str('query_scope', group='ldap', default='one')
    register_int('page_size', group='ldap', default=0)
    register_str('alias_dereferencing', group='ldap', default='default')

    register_str('user_tree_dn', group='ldap', default=None)
    register_str('user_filter', group='ldap', default=None)
    register_str('user_objectclass', group='ldap', default='inetOrgPerson')
    register_str('user_id_attribute', group='ldap', default='cn')
    register_str('user_name_attribute', group='ldap', default='sn')
    register_str('user_mail_attribute', group='ldap', default='email')
    register_str('user_pass_attribute', group='ldap', default='userPassword')
    register_str('user_enabled_attribute', group='ldap', default='enabled')
    register_str(
        'user_domain_id_attribute', group='ldap', default='businessCategory')
    register_int('user_enabled_mask', group='ldap', default=0)
    register_str('user_enabled_default', group='ldap', default='True')
    register_list(
        'user_attribute_ignore', group='ldap', default='tenant_id,tenants')
    register_bool('user_allow_create', group='ldap', default=True)
    register_bool('user_allow_update', group='ldap', default=True)
    register_bool('user_allow_delete', group='ldap', default=True)
    register_bool('user_enabled_emulation', group='ldap', default=False)
    register_str('user_enabled_emulation_dn', group='ldap', default=None)
    register_list(
        'user_additional_attribute_mapping', group='ldap', default=None)

    register_str('tenant_tree_dn', group='ldap', default=None)
    register_str('tenant_filter', group='ldap', default=None)
    register_str('tenant_objectclass', group='ldap', default='groupOfNames')
    register_str('tenant_id_attribute', group='ldap', default='cn')
    register_str('tenant_member_attribute', group='ldap', default='member')
    register_str('tenant_name_attribute', group='ldap', default='ou')
    register_str('tenant_desc_attribute', group='ldap', default='description')
    register_str('tenant_enabled_attribute', group='ldap', default='enabled')
    register_str(
        'tenant_domain_id_attribute', group='ldap', default='businessCategory')
    register_list('tenant_attribute_ignore', group='ldap', default='')
    register_bool('tenant_allow_create', group='ldap', default=True)
    register_bool('tenant_allow_update', group='ldap', default=True)
    register_bool('tenant_allow_delete', group='ldap', default=True)
    register_bool('tenant_enabled_emulation', group='ldap', default=False)
    register_str('tenant_enabled_emulation_dn', group='ldap', default=None)
    register_list(
        'tenant_additional_attribute_mapping', group='ldap', default=None)

    register_str('role_tree_dn', group='ldap', default=None)
    register_str('role_filter', group='ldap', default=None)
    register_str(
        'role_objectclass', group='ldap', default='organizationalRole')
    register_str('role_id_attribute', group='ldap', default='cn')
    register_str('role_name_attribute', group='ldap', default='ou')
    register_str('role_member_attribute', group='ldap', default='roleOccupant')
    register_list('role_attribute_ignore', group='ldap', default='')
    register_bool('role_allow_create', group='ldap', default=True)
    register_bool('role_allow_update', group='ldap', default=True)
    register_bool('role_allow_delete', group='ldap', default=True)
    register_list(
        'role_additional_attribute_mapping', group='ldap', default=None)

    register_str('group_tree_dn', group='ldap', default=None)
    register_str('group_filter', group='ldap', default=None)
    register_str('group_objectclass', group='ldap', default='groupOfNames')
    register_str('group_id_attribute', group='ldap', default='cn')
    register_str('group_name_attribute', group='ldap', default='ou')
    register_str('group_member_attribute', group='ldap', default='member')
    register_str('group_desc_attribute', group='ldap', default='description')
    register_str(
        'group_domain_id_attribute', group='ldap', default='businessCategory')
    register_list('group_attribute_ignore', group='ldap', default='')
    register_bool('group_allow_create', group='ldap', default=True)
    register_bool('group_allow_update', group='ldap', default=True)
    register_bool('group_allow_delete', group='ldap', default=True)
    register_list(
        'group_additional_attribute_mapping', group='ldap', default=None)

    register_str('domain_tree_dn', group='ldap', default=None)
    register_str('domain_filter', group='ldap', default=None)
    register_str('domain_objectclass', group='ldap', default='groupOfNames')
    register_str('domain_id_attribute', group='ldap', default='cn')
    register_str('domain_name_attribute', group='ldap', default='ou')
    register_str('domain_member_attribute', group='ldap', default='member')
    register_str('domain_desc_attribute', group='ldap', default='description')
    register_str('domain_enabled_attribute', group='ldap', default='enabled')
    register_list('domain_attribute_ignore', group='ldap', default='')
    register_bool('domain_allow_create', group='ldap', default=True)
    register_bool('domain_allow_update', group='ldap', default=True)
    register_bool('domain_allow_delete', group='ldap', default=True)
    register_bool('domain_enabled_emulation', group='ldap', default=False)
    register_str('domain_enabled_emulation_dn', group='ldap', default=None)
    register_list(
        'domain_additional_attribute_mapping', group='ldap', default=None)

    register_str('tls_cacertfile', group='ldap', default=None)
    register_str('tls_cacertdir', group='ldap', default=None)
    register_bool('use_tls', group='ldap', default=False)
    register_str('tls_req_cert', group='ldap', default='demand')

    # pam
    register_str('userid', group='pam', default=None)
    register_str('password', group='pam', default=None)

    # default authentication methods
    register_list('methods', group='auth', default=_DEFAULT_AUTH_METHODS)
    register_str(
        'password', group='auth', default='keystone.auth.plugins.token.Token')
    register_str(
        'token', group='auth',
        default='keystone.auth.plugins.password.Password')

    # register any non-default auth methods here (used by extensions, etc)
    for method_name in CONF.auth.methods:
        if method_name not in _DEFAULT_AUTH_METHODS:
            register_str(method_name, group='auth')
