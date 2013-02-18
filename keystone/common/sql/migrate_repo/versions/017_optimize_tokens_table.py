# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC
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


from migrate import *
from sqlalchemy import *
from sqlalchemy.engine import reflection


def upgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine

    token = Table('token', meta, autoload=True)

    token.create_column(Column("user_id", String(36), nullable=True))
    token.create_column(Column("tenant_id", String(36), nullable=True))

    #NOTE(bcwaldon): This does not work!
    #Index('idx_token_valid_user_id_tenant_id',
    #      token.c.user_id, token.c.tenant_id)\
    #        .create(bind=migrate_engine)

    migrate_engine.execute(token.delete())


def downgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine

    token = Table('token', meta, autoload=True)

    #NOTE(bcwaldon): This does not work!
    #Index('idx_token_valid_user_id_tenant_id').drop(bind=migrate_engine)

    token.drop_column('user_id')
    token.drop_column('tenant_id')

    migrate_engine.execute(token.delete())
