#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from keystone.common.sql import migration_control


def force_data_migration(release):
    """Migrate any data that is still in old locations.

    This method is called once all the nodes have been upgraded to the new
    release and the operator wants to finish off migrating any data that has
    not already been migrated on-the-fly. Any migration code here must be
    capable of being called repeatedly.

    :param release: name of the release (e.g. 'Newton', 'Ocata' etc.)
    :type release: string

    """
    if release == migration_control.NEWTON_RELEASE:
        # No data migrations are required for Newton
        pass
