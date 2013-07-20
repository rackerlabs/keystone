# Copyright 2013 Mirantis Inc.
# All Rights Reserved
#
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
#
# @author: Victor Sergeyev, Mirantis Inc.
#
# vim: tabstop=4 shiftwidth=4 softtabstop=4

from migrate.changeset import UniqueConstraint
from sqlalchemy import MetaData, Table


UC_DATA = (
    # table_name, old_uc_name, (columns,)
    ("group", "domain_id", ("domain_id", "name")),
    ("user", "domain_id", ("domain_id", "name")),
    ("project", "domain_id", ("domain_id", "name")),
)


def _uc_rename(migrate_engine, upgrade=True):
    meta = MetaData(bind=migrate_engine)

    for table_name, old_uc_name, columns in UC_DATA:
        table = Table(table_name, meta, autoload=True)

        new_uc_name = "uniq_{0}0{1}".format(table_name, "0".join(columns))

        if upgrade:
            old_name, new_name = old_uc_name, new_uc_name
        else:
            old_name, new_name = new_uc_name, old_uc_name

        UniqueConstraint(*columns, table=table, name=old_name).drop()
        UniqueConstraint(*columns, table=table, name=new_name).create()


def upgrade(migrate_engine):
    return _uc_rename(migrate_engine, upgrade=True)


def downgrade(migrate_engine):
    return _uc_rename(migrate_engine, upgrade=False)
