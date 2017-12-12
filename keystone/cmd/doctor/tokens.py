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

from keystone.common import fernet_utils as utils

CONF = keystone.conf.CONF


def symptom_unreasonable_max_token_size():
    """`keystone.conf [DEFAULT] max_token_size` should be adjusted.

    This option is intended to protect keystone from unreasonably sized tokens,
    where "reasonable" is mostly dependent on the `keystone.conf [token]
    provider` that you're using. If you're using one of the following token
    providers, then you should set `keystone.conf [DEFAULT] max_token_size`
    accordingly:

    - For UUID, set `keystone.conf [DEFAULT] max_token_size = 32`, because UUID
      tokens are always exactly 32 characters.

    - For Fernet, set `keystone.conf [DEFAULT] max_token_size = 255`, because
      Fernet tokens should never exceed this length in most deployments.
      However, if you are also using `keystone.conf [identity] driver = ldap`,
      Fernet tokens may not be built using an efficient packing method,
      depending on the IDs returned from LDAP, resulting in longer Fernet
      tokens (adjust your `max_token_size` accordingly).
    """
    return (
        'uuid' in CONF.token.provider and CONF.max_token_size != 32
        or 'fernet' in CONF.token.provider and CONF.max_token_size > 255)


def symptom_keys_in_token_key_repository():
    """Fernet key repository is empty.

    After configuring keystone to use the Fernet token provider, you
    should use `keystone-manage fernet_setup` to initially populate your key
    repository with keys, and periodically rotate your keys with
    `keystone-manage fernet_rotate`.
    """
    fernet_utils = utils.FernetUtils(
        CONF.fernet_tokens.key_repository,
        CONF.fernet_tokens.max_active_keys,
        'fernet_tokens'
    )
    return (
        'fernet' in CONF.token.provider
        and not fernet_utils.load_keys())


def symptom_usability_of_token_key_repository():
    """Fernet key repository is not setup correctly.

    The Fernet key repository is expected to be readable by the user running
    keystone, but not world-readable, because it contains security-sensitive
    secrets.
    """
    fernet_utils = utils.FernetUtils(
        CONF.fernet_tokens.key_repository,
        CONF.fernet_tokens.max_active_keys,
        'fernet_tokens'
    )
    return (
        'fernet' in CONF.token.provider
        and not fernet_utils.validate_key_repository())
