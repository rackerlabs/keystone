# Copyright 2016 Intel Corporation
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

from sqlalchemy import MetaData, Table

from keystone.common import sql

_ASSIGNMENT_TABLE_NAME = 'assignment'
_ASSIGNMENT_COLUMN_NAMES = ('actor_id_uuid', 'target_id_uuid', 'role_id_uuid')


def upgrade(migrate_engine):
    meta = MetaData(bind=migrate_engine)
    assignment = Table(_ASSIGNMENT_TABLE_NAME, meta, autoload=True)

    for column_name in _ASSIGNMENT_COLUMN_NAMES:
        column = sql.Column(column_name, sql.UUID(), nullable=True)
        assignment.create_column(column)
