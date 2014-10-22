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
import stat

from keyczar import keyczart
from oslo_serialization import jsonutils

from keystone import config
from keystone.i18n import _, _LE, _LW, _LI
from keystone.openstack.common import log


LOG = log.getLogger(__name__)

CONF = config.CONF


def validate_key_repository():
    """Validate permissions on the key repository directory."""
    # we need a key directory to proceed at all
    if CONF.ae_tokens.key_repository is None:
        LOG.error(_LE(
            'Set [ae_tokens] key_repository to the directory where '
            'Keystone should store encryption keys.'))
        return False

    # ensure current user has full access to the key repository
    if (not os.access(CONF.ae_tokens.key_repository, os.R_OK) or not
            os.access(CONF.ae_tokens.key_repository, os.W_OK) or not
            os.access(CONF.ae_tokens.key_repository, os.X_OK)):
        LOG.error(
            _('Insufficient permissions on [ae_tokens] key_repository: %s') % (
                CONF.ae_tokens.key_repository))
        return False

    # ensure the directory cannot be read by anyone
    stat_info = os.stat(CONF.ae_tokens.key_repository)
    if stat_info.st_mode & stat.S_IROTH or stat_info.st_mode & stat.S_IXOTH:
        LOG.warning(_LW('[ae_tokens] key_repository is world readable: %s') % (
            CONF.ae_tokens.key_repository))

    return True


def _chown_files(keystone_user_id, keystone_group_id):
    """If we're running as root, ensure everything is owned by keystone."""
    if not (keystone_user_id or keystone_group_id):
        # we only need to chown files if we're creating them as root for
        # a keystone user
        return

    os.chown(
        CONF.ae_tokens.key_repository, keystone_user_id, keystone_group_id)

    # FIXME(dolph): race condition where a primary key is added but not
    # readable by the running keystone user
    for dirpath, dirnames, filenames in os.walk(CONF.ae_tokens.key_repository):
        for f in filenames:
            os.chown(
                os.path.join(dirpath, f), keystone_user_id, keystone_group_id)


def create_key_directory(keystone_user_id=None, keystone_group_id=None):
    """If the configured key directory does not exist, attempt to create it."""
    if not os.access(CONF.ae_tokens.key_repository, os.F_OK):
        LOG.info(_LI(
            '[ae_tokens] key_repository does not appear to exist; attempting '
            'to create it'))

        try:
            os.mkdir(CONF.ae_tokens.key_repository, 0o700)
        except OSError:
            LOG.error(_LE(
                'Failed to create [ae_tokens] key_repository: either it '
                'already exists or you don\'t have sufficient permissions to '
                'create it'))

    _chown_files(keystone_user_id, keystone_group_id)


def initialize_key_repository(purpose='crypt', keystone_user_id=None,
                              keystone_group_id=None):
    """Create a key repository, and bootstrap it with a primary key."""
    meta_file = os.path.join(CONF.ae_tokens.key_repository, 'meta')

    # keyczart does not create files with a secure mode, so force 0600
    # see: https://code.google.com/p/keyczar/issues/detail?id=157
    old_umask = os.umask(0o177)
    try:
        if not os.access(meta_file, os.F_OK):
            keyczart.main([
                'create',
                '--location=%s' % CONF.ae_tokens.key_repository,
                '--purpose=%s' % purpose,
                '--name=AE'])

        keyczart.main([
            'addkey',
            '--location=%s' % CONF.ae_tokens.key_repository,
            '--status=primary'])
    finally:
        os.umask(old_umask)

    _chown_files(keystone_user_id, keystone_group_id)


def rotate_keys(keystone_user_id=None, keystone_group_id=None):
    """Create a new primary key and demote excess active keys."""
    meta_file = os.path.join(CONF.ae_tokens.key_repository, 'meta')
    with open(meta_file, 'r') as f:
        metadata = jsonutils.loads(f.read())

    active_keys = []
    inactive_keys = []
    for version in metadata['versions']:
        if version['status'] == 'ACTIVE':
            active_keys.append(version['versionNumber'])
        elif version['status'] == 'INACTIVE':
            inactive_keys.append(version['versionNumber'])

    # keyczart does not create files with a secure mode, so force 0600
    # see: https://code.google.com/p/keyczar/issues/detail?id=157
    old_umask = os.umask(0o177)
    try:
        # create a new primary key, demoting the primary key
        keyczart.main([
            'addkey',
            '--status=primary',
            '--location=%s' % CONF.ae_tokens.key_repository])
    finally:
        os.umask(old_umask)

    # demote excess active keys
    active_keys.sort()
    while len(active_keys) >= CONF.ae_tokens.max_active_keys:
        version = active_keys.pop(0)
        keyczart.main([
            'demote',
            '--location=%s' % CONF.ae_tokens.key_repository,
            '--version=%d' % version])

    # purge inactive keys
    for version in inactive_keys:
        keyczart.main([
            'revoke',
            '--location=%s' % CONF.ae_tokens.key_repository,
            '--version=%d' % version])

    _chown_files(keystone_user_id, keystone_group_id)
