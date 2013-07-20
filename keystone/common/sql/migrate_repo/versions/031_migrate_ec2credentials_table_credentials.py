# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack LLC
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

import hashlib
import json
import sqlalchemy as sql

from keystone import exception


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    sql.Table('user', meta, autoload=True)
    sql.Table('project', meta, autoload=True)
    credential_table = sql.Table('credential',
                                 meta,
                                 autoload=True)

    ec2_cred_table = sql.Table('ec2_credential',
                               meta,
                               autoload=True)

    session = sql.orm.sessionmaker(bind=migrate_engine)()
    insert = credential_table.insert()
    for ec2credential in session.query(ec2_cred_table):
        cred_exist = check_credential_exist(ec2credential,
                                            credential_table, session)

        if not cred_exist:
            dict = convert_ec2_to_v3_credential(ec2credential)
            insert.execute(dict)

    session.commit()
    session.close()

    ec2_cred_table.drop()


def convert_ec2_to_v3_credential(ec2credential):
    blob = {'access': ec2credential.access,
            'secret': ec2credential.secret}
    return {'id': hashlib.sha256(ec2credential.access).hexdigest(),
            'user_id': ec2credential.user_id,
            'project_id': ec2credential.tenant_id,
            'blob': json.dumps(blob),
            'type': 'ec2',
            'extra': json.dumps({})}


def check_credential_exist(ec2credential, credential_table, session):
    r = session.query(credential_table).filter_by(
        id=ec2credential.access).first()

    if r is not None:
        blob = json.loads(r.blob)
        if blob is not None and blob['secret'] == ec2credential['secret']:
            msg = ('Credential %s already exists in %s table' %
                   ec2credential['access'], credential_table.name)
            raise exception.Conflict(type='credential', details=msg)

    return False


def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    session = sql.orm.sessionmaker(bind=migrate_engine)()
    ec2_credential_table = sql.Table(
        'ec2_credential',
        meta,
        sql.Column('access', sql.String(64), primary_key=True),
        sql.Column('secret', sql.String(64)),
        sql.Column('user_id', sql.String(64)),
        sql.Column('tenant_id', sql.String(64)))
    ec2_credential_table.create(migrate_engine, checkfirst=True)

    # Note(nachiappan): During downgrade the credential data is not migrated
    #                   as it is not possible to distinguish between v3
    #                   credential and ec2 credential

    session.commit()
    session.close()
