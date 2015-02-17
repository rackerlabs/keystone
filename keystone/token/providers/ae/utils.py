# Copyright 2012 OpenStack Foundation
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

from keystone import config
from keystone.openstack.common import log


LOG = log.getLogger(__name__)

CONF = config.CONF


def validate_key_repository():
    """Validate permissions on the key repository directory."""
    # TODO(dolph): this is only necessary if the repo is stored on disk
    return True


def create_key_directory(keystone_user_id=None, keystone_group_id=None):
    """If the configured key directory does not exist, attempt to create it."""
    # TODO(dolph): this is only necessary if the repo is stored on disk
    pass


def initialize_key_repository(purpose='crypt', keystone_user_id=None,
                              keystone_group_id=None):
    """Create a key repository, and bootstrap it with a primary key."""
    meta_file = os.path.join(CONF.ae_tokens.key_repository, 'meta')

    old_umask = os.umask(0o177)
    try:
        if not os.access(meta_file, os.F_OK):
            # TODO(dolph): create a key repository if one does not exist
            pass

        # TODO(dolph): bootstrap the key repository with a key
        pass
    finally:
        os.umask(old_umask)


def rotate_keys(keystone_user_id=None, keystone_group_id=None):
    """Create a new primary key and demote excess active keys."""
    old_umask = os.umask(0o177)
    try:
        # TODO(dolph): create a new primary key and demote the primary key
        pass
    finally:
        os.umask(old_umask)

    # TODO(dolph): demote excess active keys
    pass

    # TODO(dolph): purge inactive keys
    pass
