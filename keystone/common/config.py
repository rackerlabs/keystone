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

import os
import sys

from oslo.config import cfg

from keystone.common import logging


_DEFAULT_LOG_FORMAT = "%(asctime)s %(levelname)8s [%(name)s] %(message)s"
_DEFAULT_LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_DEFAULT_AUTH_METHODS = ['external', 'password', 'token']

COMMON_CLI_OPTS = [
    cfg.BoolOpt('debug',
                short='d',
                default=False,
                help='Print debugging output (set logging level to '
                     'DEBUG instead of default WARNING level).'),
    cfg.BoolOpt('verbose',
                short='v',
                default=False,
                help='Print more verbose output (set logging level to '
                     'INFO instead of default WARNING level).'),
]

LOGGING_CLI_OPTS = [
    cfg.StrOpt('log-config',
               metavar='PATH',
               help='If this option is specified, the logging configuration '
                    'file specified is used and overrides any other logging '
                    'options specified. Please see the Python logging module '
                    'documentation for details on logging configuration '
                    'files.'),
    cfg.StrOpt('log-format',
               default=_DEFAULT_LOG_FORMAT,
               metavar='FORMAT',
               help='A logging.Formatter log message format string which may '
                    'use any of the available logging.LogRecord attributes.'),
    cfg.StrOpt('log-date-format',
               default=_DEFAULT_LOG_DATE_FORMAT,
               metavar='DATE_FORMAT',
               help='Format string for %%(asctime)s in log records.'),
    cfg.StrOpt('log-file',
               metavar='PATH',
               help='Name of log file to output. '
                    'If not set, logging will go to stdout.'),
    cfg.StrOpt('log-dir',
               help='The directory in which to store log files. '
                    '(will be prepended to --log-file)'),
    cfg.BoolOpt('use-syslog',
                default=False,
                help='Use syslog for logging.'),
    cfg.StrOpt('syslog-log-facility',
               default='LOG_USER',
               help='syslog facility to receive log lines.')
]

CONF = cfg.CONF


def setup_logging(conf):
    """Sets up the logging options for a log with supplied name

    :param conf: a cfg.ConfOpts object
    """

    if conf.log_config:
        # Use a logging configuration file for all settings...
        if os.path.exists(conf.log_config):
            logging.config.fileConfig(conf.log_config)
            return
        else:
            raise RuntimeError(_('Unable to locate specified logging '
                               'config file: %s') % conf.log_config)

    root_logger = logging.root
    if conf.debug:
        root_logger.setLevel(logging.DEBUG)
    elif conf.verbose:
        root_logger.setLevel(logging.INFO)
    else:
        root_logger.setLevel(logging.WARNING)

    formatter = logging.Formatter(conf.log_format, conf.log_date_format)

    if conf.use_syslog:
        try:
            facility = getattr(logging.SysLogHandler,
                               conf.syslog_log_facility)
        except AttributeError:
            raise ValueError(_('Invalid syslog facility'))

        handler = logging.SysLogHandler(address='/dev/log',
                                        facility=facility)
    elif conf.log_file:
        logfile = conf.log_file
        if conf.log_dir:
            logfile = os.path.join(conf.log_dir, logfile)
        handler = logging.WatchedFileHandler(logfile)
    else:
        handler = logging.StreamHandler(sys.stdout)

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)


def setup_authentication(conf=None):
    # register any non-default auth methods here (used by extensions, etc)
    if conf is None:
        conf = CONF
    for method_name in conf.auth.methods:
        if method_name not in _DEFAULT_AUTH_METHODS:
            conf.register_opt(cfg.StrOpt(method_name), group='auth')


def configure(conf=None):
    if conf is None:
        conf = CONF

    conf.register_cli_opts(COMMON_CLI_OPTS)
    conf.register_cli_opts(LOGGING_CLI_OPTS)

    conf.register_cli_opt(
        cfg.BoolOpt('standard-threads', default=False,
                    help='Do not monkey-patch threading system modules.'))
    conf.register_cli_opt(
        cfg.StrOpt('pydev-debug-host', default=None,
                   help='Host to connect to for remote debugger.'))
    conf.register_cli_opt(
        cfg.IntOpt('pydev-debug-port', default=None,
                   help='Port to connect to for remote debugger.'))

    general_opts = [cfg.StrOpt('admin_token', secret=True, default='ADMIN'),
                    cfg.StrOpt('bind_host', default='0.0.0.0'),
                    cfg.IntOpt('compute_port', default=8774),
                    cfg.IntOpt('admin_port', default=35357),
                    cfg.IntOpt('public_port', default=5000),
                    cfg.StrOpt('public_endpoint',
                               default='http://localhost:%(public_port)s/'),
                    cfg.StrOpt('admin_endpoint',
                               default='http://localhost:%(admin_port)s/'),
                    cfg.StrOpt('onready'),
                    cfg.StrOpt('auth_admin_prefix', default=''),
                    cfg.StrOpt('policy_file', default='policy.json'),
                    cfg.StrOpt('policy_default_rule', default=None),
                    # default max request size is 112k
                    cfg.IntOpt('max_request_body_size', default=114688),
                    cfg.IntOpt('max_param_size', default=64),
                    # we allow tokens to be a bit larger to accommodate PKI
                    cfg.IntOpt('max_token_size', default=8192),
                    cfg.StrOpt('member_role_id',
                               default='9fe2ff9ee4384b1894a90878d3e92bab'),
                    cfg.StrOpt('member_role_name', default='_member_'),
                    cfg.IntOpt('crypt_strength', default=40000)]
    for opt in general_opts:
        conf.register_opt(opt)

    identity_opts = [cfg.StrOpt('default_domain_id', default='default'),
                     cfg.BoolOpt('domain_specific_drivers_enabled',
                                 default=False),
                     cfg.StrOpt('domain_config_dir',
                                default='/etc/keystone/domains'),
                     cfg.StrOpt('driver',
                                default=('keystone.identity.backends'
                                         '.sql.Identity')),
                     cfg.IntOpt('max_password_length', default=4096)]
    for opt in identity_opts:
        conf.register_opt(opt, group='identity')

    trust_opts = [cfg.BoolOpt('enabled', default=True),
                  cfg.StrOpt('driver',
                             default='keystone.trust.backends.sql.Trust')]
    for opt in trust_opts:
        conf.register_opt(opt, group='trust')

    os_inherit_opts = [cfg.BoolOpt('enabled', default=False)]
    for opt in os_inherit_opts:
        conf.register_opt(opt, group='os_inherit')

    token_opts = [cfg.ListOpt('bind', default=[]),
                  cfg.StrOpt('enforce_token_bind', default='permissive'),
                  cfg.IntOpt('expiration', default=86400),
                  cfg.StrOpt('provider', default=None),
                  cfg.StrOpt('driver',
                             default='keystone.token.backends.sql.Token')]
    for opt in token_opts:
        conf.register_opt(opt, group='token')

    ssl_opts = [cfg.BoolOpt('enable', default=False),
                cfg.StrOpt('certfile',
                           default="/etc/keystone/ssl/certs/keystone.pem"),
                cfg.StrOpt(
                    'keyfile',
                    default="/etc/keystone/ssl/private/keystonekey.pem"),
                cfg.StrOpt('ca_certs',
                           default="/etc/keystone/ssl/certs/ca.pem"),
                cfg.StrOpt('ca_key',
                           default="/etc/keystone/ssl/certs/cakey.pem"),
                cfg.BoolOpt('cert_required', default=False),
                cfg.IntOpt('key_size', default=1024),
                cfg.IntOpt('valid_days', default=3650),
                cfg.StrOpt('ca_password', default=None),
                cfg.StrOpt(
                    'cert_subject',
                    default='/C=US/ST=Unset/L=Unset/O=Unset/CN=localhost')]
    for opt in ssl_opts:
        conf.register_opt(opt, group='ssl')

    signing_opts = [cfg.StrOpt('token_format', default=None),
                    cfg.StrOpt(
                        'certfile',
                        default="/etc/keystone/ssl/certs/signing_cert.pem"),
                    cfg.StrOpt(
                        'keyfile',
                        default="/etc/keystone/ssl/private/signing_key.pem"),
                    cfg.StrOpt('ca_certs',
                               default="/etc/keystone/ssl/certs/ca.pem"),
                    cfg.StrOpt('ca_key',
                               default="/etc/keystone/ssl/certs/cakey.pem"),
                    cfg.IntOpt('key_size', default=2048),
                    cfg.IntOpt('valid_days', default=3650),
                    cfg.StrOpt('ca_password', default=None),
                    cfg.StrOpt('cert_subject',
                               default=('/C=US/ST=Unset/L=Unset/O=Unset/'
                                        'CN=www.example.com'))]
    for opt in signing_opts:
        conf.register_opt(opt, group='signing')

    sql_opts = [cfg.StrOpt('connection', secret=True,
                           default='sqlite:///keystone.db'),
                cfg.IntOpt('idle_timeout', default=200)]
    for opt in sql_opts:
        conf.register_opt(opt, group='sql')

    #assignment has no default for backward compatibility reasons.
    #If assignment is not specified, the identity driver chooses the backend
    assignment_opts = [cfg.StrOpt('driver', default=None)]
    for opt in assignment_opts:
        conf.register_opt(opt, group='assignment')

    cred_opts = [cfg.StrOpt('driver',
                            default=('keystone.credential.backends'
                                     '.sql.Credential'))]
    for opt in cred_opts:
        conf.register_opt(opt, group='credential')

    policy_opts = [cfg.StrOpt('driver',
                              default='keystone.policy.backends.sql.Policy')]
    for opt in policy_opts:
        conf.register_opt(opt, group='policy')

    ec2_opts = [cfg.StrOpt('driver',
                           default='keystone.contrib.ec2.backends.kvs.Ec2')]
    for opt in ec2_opts:
        conf.register_opt(opt, group='ec2')

    stats_opts = [cfg.StrOpt('driver',
                             default=('keystone.contrib.stats.backends'
                                      '.kvs.Stats'))]
    for opt in stats_opts:
        conf.register_opt(opt, group='stats')

    ldap_opts = [cfg.StrOpt('url', default='ldap://localhost'),
                 cfg.StrOpt('user', default=None),
                 cfg.StrOpt('password', secret=True, default=None),
                 cfg.StrOpt('suffix', default='cn=example,cn=com'),
                 cfg.BoolOpt('use_dumb_member', default=False),
                 cfg.StrOpt('dumb_member', default='cn=dumb,dc=nonexistent'),
                 cfg.BoolOpt('allow_subtree_delete', default=False),
                 cfg.StrOpt('query_scope', default='one'),
                 cfg.IntOpt('page_size', default=0),
                 cfg.StrOpt('alias_dereferencing', default='default'),

                 cfg.StrOpt('user_tree_dn', default=None),
                 cfg.StrOpt('user_filter', default=None),
                 cfg.StrOpt('user_objectclass', default='inetOrgPerson'),
                 cfg.StrOpt('user_id_attribute', default='cn'),
                 cfg.StrOpt('user_name_attribute', default='sn'),
                 cfg.StrOpt('user_mail_attribute', default='email'),
                 cfg.StrOpt('user_pass_attribute', default='userPassword'),
                 cfg.StrOpt('user_enabled_attribute', default='enabled'),
                 cfg.StrOpt('user_domain_id_attribute',
                            default='businessCategory'),
                 cfg.IntOpt('user_enabled_mask', default=0),
                 cfg.StrOpt('user_enabled_default', default='True'),
                 cfg.ListOpt('user_attribute_ignore',
                             default='tenant_id,tenants'),
                 cfg.BoolOpt('user_allow_create', default=True),
                 cfg.BoolOpt('user_allow_update', default=True),
                 cfg.BoolOpt('user_allow_delete', default=True),
                 cfg.BoolOpt('user_enabled_emulation', default=False),
                 cfg.StrOpt('user_enabled_emulation_dn', default=None),
                 cfg.ListOpt('user_additional_attribute_mapping',
                             default=None),

                 cfg.StrOpt('tenant_tree_dn', default=None),
                 cfg.StrOpt('tenant_filter', default=None),
                 cfg.StrOpt('tenant_objectclass', default='groupOfNames'),
                 cfg.StrOpt('tenant_id_attribute', default='cn'),
                 cfg.StrOpt('tenant_member_attribute', default='member'),
                 cfg.StrOpt('tenant_name_attribute', default='ou'),
                 cfg.StrOpt('tenant_desc_attribute', default='description'),
                 cfg.StrOpt('tenant_enabled_attribute', default='enabled'),
                 cfg.StrOpt('tenant_domain_id_attribute',
                            default='businessCategory'),
                 cfg.ListOpt('tenant_attribute_ignore', default=''),
                 cfg.BoolOpt('tenant_allow_create', default=True),
                 cfg.BoolOpt('tenant_allow_update', default=True),
                 cfg.BoolOpt('tenant_allow_delete', default=True),
                 cfg.BoolOpt('tenant_enabled_emulation', default=False),
                 cfg.StrOpt('tenant_enabled_emulation_dn', default=None),
                 cfg.ListOpt('tenant_additional_attribute_mapping',
                             default=None),

                 cfg.StrOpt('role_tree_dn', default=None),
                 cfg.StrOpt('role_filter', default=None),
                 cfg.StrOpt('role_objectclass', default='organizationalRole'),
                 cfg.StrOpt('role_id_attribute', default='cn'),
                 cfg.StrOpt('role_name_attribute', default='ou'),
                 cfg.StrOpt('role_member_attribute', default='roleOccupant'),
                 cfg.ListOpt('role_attribute_ignore', default=''),
                 cfg.BoolOpt('role_allow_create', default=True),
                 cfg.BoolOpt('role_allow_update', default=True),
                 cfg.BoolOpt('role_allow_delete', default=True),
                 cfg.ListOpt('role_additional_attribute_mapping',
                             default=None),

                 cfg.StrOpt('group_tree_dn', default=None),
                 cfg.StrOpt('group_filter', default=None),
                 cfg.StrOpt('group_objectclass', default='groupOfNames'),
                 cfg.StrOpt('group_id_attribute', default='cn'),
                 cfg.StrOpt('group_name_attribute', default='ou'),
                 cfg.StrOpt('group_member_attribute', default='member'),
                 cfg.StrOpt('group_desc_attribute', default='description'),
                 cfg.StrOpt('group_domain_id_attribute',
                            default='businessCategory'),
                 cfg.ListOpt('group_attribute_ignore', default=''),
                 cfg.BoolOpt('group_allow_create', default=True),
                 cfg.BoolOpt('group_allow_update', default=True),
                 cfg.BoolOpt('group_allow_delete', default=True),
                 cfg.ListOpt('group_additional_attribute_mapping',
                             default=None),

                 cfg.StrOpt('tls_cacertfile', default=None),
                 cfg.StrOpt('tls_cacertdir', default=None),
                 cfg.BoolOpt('use_tls', default=False),
                 cfg.StrOpt('tls_req_cert', default='demand')]
    for opt in ldap_opts:
        conf.register_opt(opt, group='ldap')

    pam_opts = [cfg.StrOpt('userid', default=None),
                cfg.StrOpt('password', default=None)]
    for opt in pam_opts:
        conf.register_opt(opt, group='pam')

    auth_opts = [cfg.ListOpt('methods', default=_DEFAULT_AUTH_METHODS),
                 cfg.StrOpt('password',
                            default='keystone.auth.plugins.token.Token'),
                 cfg.StrOpt('token',
                            default='keystone.auth.plugins.password.Password'),
                 #deals with REMOTE_USER authentication
                 cfg.StrOpt(
                     'external',
                     default='keystone.auth.plugins.external.ExternalDefault')]
    for opt in auth_opts:
        conf.register_opt(opt, group='auth')

    # register any non-default auth methods here (used by extensions, etc)
    setup_authentication(conf)

    paste_deploy_opts = [cfg.StrOpt('config_file', default=None)]
    for opt in paste_deploy_opts:
        conf.register_opt(opt, group='paste_deploy')

    memcache_opts = [cfg.StrOpt('servers', default='localhost:11211'),
                     cfg.IntOpt('max_compare_and_set_retry', default=16)]
    for opt in memcache_opts:
        conf.register_opt(opt, group='memcache')

    catalog_opts = [cfg.StrOpt('template_file',
                               default='default_catalog.templates'),
                    cfg.StrOpt(
                        'driver',
                        default='keystone.catalog.backends.sql.Catalog')]
    for opt in catalog_opts:
        conf.register_opt(opt, group='catalog')
