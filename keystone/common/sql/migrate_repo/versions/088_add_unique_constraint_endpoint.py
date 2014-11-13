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

import migrate
from oslo_log import log
import sqlalchemy as sql

from keystone.i18n import _LE


LOG = log.getLogger(__name__)


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    endpoint_table_name = 'endpoint'
    endpoint_table = sql.Table(endpoint_table_name, meta, autoload=True)
    try:
        migrate.UniqueConstraint(endpoint_table.c.service_id,
                                 endpoint_table.c.region_id,
                                 endpoint_table.c.interface).create()
    except Exception as e:
        LOG.error(_LE('There was an error when trying to create the unique '
                      'constraint at the endpoint table: "%s". There might '
                      'be duplicate endpoint entries. Please remove them '
                      'before upgrading.') % e)
        raise(e)
