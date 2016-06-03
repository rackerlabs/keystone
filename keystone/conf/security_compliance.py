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
    cfg.IntOpt('disable_user_account_days_inactive',
               default=0,
               help='Number of days for which a user can be inactive '
                    'before the account becomes disabled. Setting the '
                    'value to 0 disables this feature.'),
    cfg.IntOpt('lockout_failure_attempts',
               default=0,
               help='Number of times a user can fail login attempts until '
                    'the user account is locked. Setting the value to 0  '
                    'disables this feature.'),
    cfg.IntOpt('lockout_duration',
               default=1800,
               help='Number of seconds a user account will be locked.'),
    cfg.IntOpt('password_expires_days',
               default=0,
               help='Number of days for which a password will be '
                    'considered valid before requiring the user to '
                    'change it. Setting the value to 0 disables this '
                    'feature. Note: this feature is only supported '
                    'via the SQL backend driver for identity.'),
    cfg.IntOpt('unique_last_password_count',
               default=0,
               help='Number of latest password iterations for which the '
                    'password must be unique. Setting the value to 0 '
                    'disables this feature. Note: this feature is only '
                    'supported via the SQL backend driver for identity.'),
    cfg.IntOpt('password_change_limit_per_day',
               default=0,
               help='Maximum number of times a user can change their '
                    'password in a day. Setting the value to 0 disables '
                    'this feature.'),
    cfg.StrOpt('password_regex',
               default=None,
               help='Regular expression used to validate password '
                    'strength requirements. Setting the value to '
                    'None disables this feature. The following '
                    'is an example of a pattern which requires '
                    'at least 1 letter, 1 digit, and have a minimum '
                    'length of 7 characters: '
                    '^(?=.*\d)(?=.*[a-zA-Z]).{7,}$')
]


def register_opts(conf):
    conf.register_opts(ALL_OPTS, group=GROUP_NAME)


def list_opts():
    return {GROUP_NAME: ALL_OPTS}
