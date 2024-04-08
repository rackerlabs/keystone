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

enforce_key_length = cfg.BoolOpt(
    'enforce_key_length',
    default=True,
    help=utils.fmt("""
A boolean flag defaulting to True that toggles whether a minimum key length
of 128 bits is enforced for TOTP secrets. Only disable if your existing TOTP
secrets are smaller than the enforced 128 bits.
"""))
included_previous_windows = cfg.IntOpt(
    'included_previous_windows',
    default=1,
    min=0,
    max=10,
    help=utils.fmt(
        """
The number of previous windows to check when processing TOTP passcodes.
"""
    ),
)


GROUP_NAME = __name__.split('.')[-1]
ALL_OPTS = [
    enforce_key_length,
    included_previous_windows,
]


def register_opts(conf):
    conf.register_opts(ALL_OPTS, group=GROUP_NAME)


def list_opts():
    return {GROUP_NAME: ALL_OPTS}
