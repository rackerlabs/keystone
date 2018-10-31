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

from oslo_log import log

LOG = log.getLogger(__name__)


def create_directory(directory, keystone_user_id=None, keystone_group_id=None):
    """Attempt to create a directory if it doesn't exist.

    :param directory: string containing the path of the directory to create.
    :param keystone_user_id: the system ID of the process running keystone.
    :param keystone_group_id: the system ID of the group running keystone.

    """

    if not os.access(directory, os.F_OK):
        LOG.info(
            '%s does not appear to exist; attempting to create it', directory
        )

        try:
            os.makedirs(directory, 0o700)
        except OSError:
            LOG.error(
                'Failed to create %s: either it already '
                'exists or you don\'t have sufficient permissions to '
                'create it', directory
            )

        if keystone_user_id and keystone_group_id:
            os.chown(
                directory,
                keystone_user_id,
                keystone_group_id)
        elif keystone_user_id or keystone_group_id:
            LOG.warning(
                'Unable to change the ownership of key repository without '
                'a keystone user ID and keystone group ID both being '
                'provided: %s', directory)
