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

import keystone.conf

from keystone.common import token_utils as utils


CONF = keystone.conf.CONF


def symptom_usability_of_token_key_repository():
    """Token key repository is not setup correctly.

    The token key repository is expected to be readable by the user running
    keystone, but not world-readable, because it contains security-sensitive
    secrets.
    """
    token_utils = utils.TokenUtils(
        CONF.token_provider.key_repository,
        CONF.token_provider.max_active_keys,
        'token_provider'
    )
    return (
        'fernet' in CONF.token.provider
        and not token_utils.validate_key_repository())


def symptom_keys_in_token_key_repository():
    """Token key repository is empty.

    After configuring keystone to use a token provider, you should use
    `keystone-manage token_setup` to initially populate your key repository
    with keys, and periodically rotate your keys with `keystone-manage
    token_rotate`.
    """
    token_utils = utils.TokenUtils(
        CONF.token_provider.key_repository,
        CONF.token_provider.max_active_keys,
        'token_provider'
    )
    return (
        'fernet' in CONF.token.provider
        and not token_utils.load_keys())
