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


disable_user_account_days_inactive = cfg.IntOpt(
    'disable_user_account_days_inactive',
    default=0,
    help=utils.fmt("""
Number of days for which a user can be inactive before the account becomes
disabled. Setting the value to 0 disables this feature.
"""))

lockout_failure_attempts = cfg.IntOpt(
    'lockout_failure_attempts',
    default=0,
    help=utils.fmt("""
Number of times a user can fail login attempts until the user account is
locked. Setting the value to 0  disables this feature.
"""))

lockout_duration = cfg.IntOpt(
    'lockout_duration',
    default=1800,
    help=utils.fmt("""
Number of seconds a user account will be locked.
"""))

password_expires_days = cfg.IntOpt(
    'password_expires_days',
    default=None,
    min=1,
    help=utils.fmt("""
Number of days for which a password will be considered valid. For example,
if you set this for 90 days, all new passwords would expire in 90 days.
This feature is disabled by default. Note: this feature is only supported
via the SQL backend driver for identity.
"""))

password_expires_ignore_list = cfg.StrOpt(
    'password_expires_ignore_list',
    default=None,
    help=utils.fmt("""
Comma separated list of user IDs to be ignored when checking if a password
is expired. Thus, new passwords will not expire for users entered here.
This feature will only be enabled if password_expires_days is set.
"""))

unique_last_password_count = cfg.IntOpt(
    'unique_last_password_count',
    default=0,
    help=utils.fmt("""
Number of latest password iterations for which the password must be unique.
Setting the value to 0 disables this feature. Note: this feature is only
supported via the SQL backend driver for identity.
"""))

password_change_limit_per_day = cfg.IntOpt(
    'password_change_limit_per_day',
    default=0,
    help=utils.fmt("""
Maximum number of times a user can change their password in a day. Setting the
value to 0 disables this feature.
"""))

password_regex = cfg.StrOpt(
    'password_regex',
    default=None,
    help=utils.fmt("""
Regular expression used to validate password strength requirements. Setting the
value to None disables this feature. The following is an example of a pattern
which requires at least 1 letter, 1 digit, and have a minimum length of 7
characters: ^(?=.*\d)(?=.*[a-zA-Z]).{7,}$
"""))


GROUP_NAME = __name__.split('.')[-1]
ALL_OPTS = [
    disable_user_account_days_inactive,
    lockout_failure_attempts,
    lockout_duration,
    password_expires_days,
    password_expires_ignore_list,
    unique_last_password_count,
    password_change_limit_per_day,
    password_regex,
]


def register_opts(conf):
    conf.register_opts(ALL_OPTS, group=GROUP_NAME)


def list_opts():
    return {GROUP_NAME: ALL_OPTS}
