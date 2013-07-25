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

    conf.register_opt(cfg.StrOpt('admin_token', secret=True, default='ADMIN'))
    conf.register_opt(cfg.StrOpt('bind_host', default='0.0.0.0'))
    conf.register_opt(cfg.IntOpt('compute_port', default=8774))
    conf.register_opt(cfg.IntOpt('admin_port', default=35357))
    conf.register_opt(cfg.BoolOpt('public_port', default=5000))
    conf.register_opt(cfg.StrOpt(
        'public_endpoint',
        default='http://localhost:%(public_port)s/'))
    conf.register_opt(cfg.StrOpt('admin_endpoint',
                      default='http://localhost:%(admin_port)s/'))
    conf.register_opt(cfg.StrOpt('onready'))
    conf.register_opt(cfg.StrOpt('auth_admin_prefix', default=''))
    conf.register_opt(cfg.StrOpt('policy_file', default='policy.json'))
    conf.register_opt(cfg.StrOpt('policy_default_rule', default=None))
    # default max request size is 112k
    conf.register_opt(cfg.IntOpt('max_request_body_size', default=114688))
    conf.register_opt(cfg.IntOpt('max_param_size', default=64))
    # we allow tokens to be a bit larger to accommodate PKI
    conf.register_opt(cfg.IntOpt('max_token_size', default=8192))
    conf.register_opt(cfg.StrOpt('member_role_id',
                                 default='9fe2ff9ee4384b1894a90878d3e92bab'))
    conf.register_opt(cfg.StrOpt('member_role_name', default='_member_'))

    # identity
    conf.register_opt(cfg.BoolOpt('default_domain_id', default='default'),
                      group='identity')
    conf.register_opt(cfg.StrOpt('domain_specific_drivers_enabled',
                                 default=False),
                      group='identity')
    conf.register_opt(cfg.StrOpt('domain_config_dir',
                                 default='/etc/keystone/domains'),
                      group='identity')

    # trust
    conf.register_opt(cfg.BoolOpt('enabled', default=True), group='trust')

    # os_inherit
    conf.register_opt(cfg.BoolOpt('enabled', default=False),
                      group='os_inherit')

    # binding
    conf.register_opt(cfg.ListOpt('bind', default=[]), group='token')
    conf.register_opt(cfg.StrOpt('enforce_token_bind', default='permissive'),
                      group='token')

    # ssl
    conf.register_opt(cfg.BoolOpt('enable', default=False), group='ssl')
    conf.register_opt(
        cfg.StrOpt('certfile', default="/etc/keystone/ssl/certs/keystone.pem"),
        group='ssl')
    conf.register_opt(
        cfg.StrOpt('keyfile',
                   default="/etc/keystone/ssl/private/keystonekey.pem"),
        group='ssl')
    conf.register_opt(
        cfg.StrOpt('ca_certs', default="/etc/keystone/ssl/certs/ca.pem"),
        group='ssl')
    conf.register_opt(
        cfg.StrOpt('ca_key', default="/etc/keystone/ssl/certs/cakey.pem"),
        group='ssl')
    conf.register_opt(cfg.BoolOpt('cert_required', default=False), group='ssl')
    conf.register_opt(cfg.IntOpt('key_size', default=1024), group='ssl')
    conf.register_opt(cfg.IntOpt('valid_days', default=3650), group='ssl')
    conf.register_opt(cfg.StrOpt('ca_password', default=None), group='ssl')
    conf.register_opt(
        cfg.StrOpt('cert_subject',
                   default='/C=US/ST=Unset/L=Unset/O=Unset/CN=localhost'),
        group='ssl')

    # signing
    conf.register_opt(cfg.StrOpt('token_format', default=None),
                      group='signing')
    conf.register_opt(
        cfg.StrOpt('certfile',
                   default="/etc/keystone/ssl/certs/signing_cert.pem"),
        group='signing')
    conf.register_opt(
        cfg.StrOpt('keyfile',
                   default="/etc/keystone/ssl/private/signing_key.pem"),
        group='signing')
    conf.register_opt(
        cfg.StrOpt('ca_certs', default="/etc/keystone/ssl/certs/ca.pem"),
        group='signing')
    conf.register_opt(
        cfg.StrOpt('ca_key', default="/etc/keystone/ssl/certs/cakey.pem"),
        group='signing')
    conf.register_opt(cfg.IntOpt('key_size', default=2048), group='signing')
    conf.register_opt(cfg.IntOpt('valid_days', default=3650), group='signing')
    conf.register_opt(cfg.StrOpt('ca_password', default=None), group='signing')
    conf.register_opt(
        cfg.StrOpt(
            'cert_subject',
            default='/C=US/ST=Unset/L=Unset/O=Unset/CN=www.example.com'),
        group='signing')

    # sql
    conf.register_opt(
        cfg.StrOpt('connection', secret=True, default='sqlite:///keystone.db'),
        group='sql')
    conf.register_opt(cfg.IntOpt('idle_timeout', default=200), group='sql')

    # driver

    #assignment has no default for backward compatibility reasons.
    #If assignment is not specified, the identity driver chooses the backend
    conf.register_opt(
        cfg.StrOpt('driver', default=None),
        group='assignment')
    conf.register_opt(
        cfg.StrOpt('driver',
                   default='keystone.catalog.backends.sql.Catalog'),
        group='catalog')
    conf.register_opt(
        cfg.StrOpt('driver',
                   default='keystone.identity.backends.sql.Identity'),
        group='identity')
    conf.register_opt(
        cfg.StrOpt('driver',
                   default='keystone.credential.backends.sql.Credential'),
        group='credential')
    conf.register_opt(
        cfg.StrOpt('driver', default='keystone.policy.backends.sql.Policy'),
        group='policy')
    conf.register_opt(
        cfg.StrOpt('driver', default='keystone.token.backends.sql.Token'),
        group='token')
    conf.register_opt(
        cfg.StrOpt('driver', default='keystone.trust.backends.sql.Trust'),
        group='trust')
    conf.register_opt(
        cfg.StrOpt('driver', default='keystone.contrib.ec2.backends.kvs.Ec2'),
        group='ec2')
    conf.register_opt(
        cfg.StrOpt('driver',
                   default='keystone.contrib.stats.backends.kvs.Stats'),
        group='stats')

    # ldap
    conf.register_opt(cfg.StrOpt('url', default='ldap://localhost'),
                      group='ldap')
    conf.register_opt(cfg.StrOpt('user', default=None),
                      group='ldap')
    conf.register_opt(cfg.StrOpt('password', secret=True, default=None),
                      group='ldap')
    conf.register_opt(cfg.StrOpt('suffix', default='cn=example,cn=com'),
                      group='ldap')
    conf.register_opt(cfg.BoolOpt('use_dumb_member', default=False),
                      group='ldap')
    conf.register_opt(
        cfg.StrOpt('dumb_member', default='cn=dumb,dc=nonexistent'),
        group='ldap')
    conf.register_opt(cfg.BoolOpt('allow_subtree_delete', default=False),
                      group='ldap')
    conf.register_opt(cfg.StrOpt('query_scope', default='one'), group='ldap')
    conf.register_opt(cfg.IntOpt('page_size', default=0), group='ldap')
    conf.register_opt(cfg.StrOpt('alias_dereferencing', default='default'),
                      group='ldap')

    conf.register_opt(cfg.StrOpt('user_tree_dn', default=None), group='ldap')
    conf.register_opt(cfg.StrOpt('user_filter', default=None), group='ldap')
    conf.register_opt(cfg.StrOpt('user_objectclass', default='inetOrgPerson'),
                      group='ldap')
    conf.register_opt(cfg.StrOpt('user_id_attribute', default='cn'),
                      group='ldap')
    conf.register_opt(cfg.StrOpt('user_name_attribute', default='sn'),
                      group='ldap')
    conf.register_opt(cfg.StrOpt('user_mail_attribute', default='email'),
                      group='ldap')
    conf.register_opt(
        cfg.StrOpt('user_pass_attribute', default='userPassword'),
        group='ldap')
    conf.register_opt(cfg.StrOpt('user_enabled_attribute', default='enabled'),
                      group='ldap')
    conf.register_opt(
        cfg.StrOpt('user_domain_id_attribute', default='businessCategory'),
        group='ldap')
    conf.register_opt(cfg.IntOpt('user_enabled_mask', default=0), group='ldap')
    conf.register_opt(
        cfg.StrOpt('user_enabled_default', default='True'),
        group='ldap')
    conf.register_opt(
        cfg.ListOpt('user_attribute_ignore', default='tenant_id,tenants'),
        group='ldap')
    conf.register_opt(cfg.BoolOpt('user_allow_create', default=True),
                      group='ldap')
    conf.register_opt(cfg.BoolOpt('user_allow_update', default=True),
                      group='ldap')
    conf.register_opt(cfg.BoolOpt('user_allow_delete', default=True),
                      group='ldap')
    conf.register_opt(cfg.BoolOpt('user_enabled_emulation', default=False),
                      group='ldap')
    conf.register_opt(cfg.StrOpt('user_enabled_emulation_dn', default=None),
                      group='ldap')
    conf.register_opt(
        cfg.ListOpt('user_additional_attribute_mapping', default=None),
        group='ldap')

    conf.register_opt(cfg.StrOpt('tenant_tree_dn', default=None), group='ldap')
    conf.register_opt(cfg.StrOpt('tenant_filter', default=None), group='ldap')
    conf.register_opt(cfg.StrOpt('tenant_objectclass', default='groupOfNames'),
                      group='ldap')
    conf.register_opt(cfg.StrOpt('tenant_id_attribute', default='cn'),
                      group='ldap')
    conf.register_opt(cfg.StrOpt('tenant_member_attribute', default='member'),
                      group='ldap')
    conf.register_opt(cfg.StrOpt('tenant_name_attribute', default='ou'),
                      group='ldap')
    conf.register_opt(
        cfg.StrOpt('tenant_desc_attribute', default='description'),
        group='ldap')
    conf.register_opt(
        cfg.StrOpt('tenant_enabled_attribute', default='enabled'),
        group='ldap')
    conf.register_opt(
        cfg.StrOpt('tenant_domain_id_attribute', default='businessCategory'),
        group='ldap')
    conf.register_opt(cfg.ListOpt('tenant_attribute_ignore', default=''),
                      group='ldap')
    conf.register_opt(cfg.BoolOpt('tenant_allow_create', default=True),
                      group='ldap')
    conf.register_opt(cfg.BoolOpt('tenant_allow_update', default=True),
                      group='ldap')
    conf.register_opt(cfg.BoolOpt('tenant_allow_delete', default=True),
                      group='ldap')
    conf.register_opt(cfg.BoolOpt('tenant_enabled_emulation', default=False),
                      group='ldap')
    conf.register_opt(cfg.StrOpt('tenant_enabled_emulation_dn', default=None),
                      group='ldap')
    conf.register_opt(
        cfg.ListOpt('tenant_additional_attribute_mapping', default=None),
        group='ldap')

    conf.register_opt(cfg.StrOpt('role_tree_dn', default=None), group='ldap')
    conf.register_opt(cfg.StrOpt('role_filter', default=None), group='ldap')
    conf.register_opt(
        cfg.StrOpt('role_objectclass', default='organizationalRole'),
        group='ldap')
    conf.register_opt(cfg.StrOpt('role_id_attribute', default='cn'),
                      group='ldap')
    conf.register_opt(cfg.StrOpt('role_name_attribute', default='ou'),
                      group='ldap')
    conf.register_opt(
        cfg.StrOpt('role_member_attribute', default='roleOccupant'),
        group='ldap')
    conf.register_opt(cfg.ListOpt('role_attribute_ignore', default=''),
                      group='ldap')
    conf.register_opt(cfg.BoolOpt('role_allow_create', default=True),
                      group='ldap')
    conf.register_opt(cfg.BoolOpt('role_allow_update', default=True),
                      group='ldap')
    conf.register_opt(cfg.BoolOpt('role_allow_delete', default=True),
                      group='ldap')
    conf.register_opt(
        cfg.ListOpt('role_additional_attribute_mapping', default=None),
        group='ldap')

    conf.register_opt(cfg.StrOpt('group_tree_dn', default=None), group='ldap')
    conf.register_opt(cfg.StrOpt('group_filter', default=None), group='ldap')
    conf.register_opt(
        cfg.StrOpt('group_objectclass', default='groupOfNames'),
        group='ldap')
    conf.register_opt(cfg.StrOpt('group_id_attribute', default='cn'),
                      group='ldap')
    conf.register_opt(cfg.StrOpt('group_name_attribute', default='ou'),
                      group='ldap')
    conf.register_opt(cfg.StrOpt('group_member_attribute', default='member'),
                      group='ldap')
    conf.register_opt(
        cfg.StrOpt('group_desc_attribute', default='description'),
        group='ldap')
    conf.register_opt(
        cfg.StrOpt('group_domain_id_attribute', default='businessCategory'),
        group='ldap')
    conf.register_opt(cfg.ListOpt('group_attribute_ignore', default=''),
                      group='ldap')
    conf.register_opt(cfg.BoolOpt('group_allow_create', default=True),
                      group='ldap')
    conf.register_opt(cfg.BoolOpt('group_allow_update', default=True),
                      group='ldap')
    conf.register_opt(cfg.BoolOpt('group_allow_delete', default=True),
                      group='ldap')
    conf.register_opt(
        cfg.ListOpt('group_additional_attribute_mapping', default=None),
        group='ldap')

    conf.register_opt(cfg.StrOpt('tls_cacertfile', default=None), group='ldap')
    conf.register_opt(cfg.StrOpt('tls_cacertdir', default=None), group='ldap')
    conf.register_opt(cfg.BoolOpt('use_tls', default=False), group='ldap')
    conf.register_opt(cfg.StrOpt('tls_req_cert', default='demand'),
                      group='ldap')

    # pam
    conf.register_opt(cfg.StrOpt('userid', default=None), group='pam')
    conf.register_opt(cfg.StrOpt('password', default=None), group='pam')

    # default authentication methods
    conf.register_opt(
        cfg.ListOpt('methods', default=_DEFAULT_AUTH_METHODS), group='auth')
    conf.register_opt(
        cfg.StrOpt('password', default='keystone.auth.plugins.token.Token'),
        group='auth')
    conf.register_opt(
        cfg.StrOpt('token', default='keystone.auth.plugins.password.Password'),
        group='auth')
    #deals with REMOTE_USER authentication
    conf.register_opt(
        cfg.StrOpt('external',
                   default='keystone.auth.plugins.external.ExternalDefault'),
        group='auth')
    # register any non-default auth methods here (used by extensions, etc)
    for method_name in conf.auth.methods:
        if method_name not in _DEFAULT_AUTH_METHODS:
            conf.register_opt(cfg.StrOpt(method_name), group='auth')

    # PasteDeploy config file
    conf.register_opt(cfg.StrOpt('config_file', default=None),
                      group='paste_deploy')

    # token provider
    conf.register_opt(cfg.StrOpt('provider', default=None), group='token')

    # memcache
    conf.register_opt(
        cfg.StrOpt('servers', default='localhost:11211'), group='memcache')
    conf.register_opt(
        cfg.IntOpt('max_compare_and_set_retry', default=16), group='memcache')

    # misc
    conf.register_opt(
        cfg.StrOpt('template_file', default='default_catalog.templates'),
        group='catalog')
    conf.register_opt(cfg.IntOpt('crypt_strength', default=40000))
    conf.register_opt(cfg.IntOpt('expiration', default=86400), group='token')
