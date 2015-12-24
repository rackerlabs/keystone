mport sqlalchemy as sql

from keystone.common.sql import migration_helpers


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    identity_table = sql.Table(
        'identity',
        meta,
        sql.Column('identity_id', sql.String(64), primary_key=True,
                   nullable=False),
        sql.Column('extra', sql.Text(), nullable=True),
        sql.Column('enabled', sql.Boolean, nullable=False, default=True))
    identity_table.create(migrate_engine, checkfirst=True)

    password_table = sql.Table(
        'password',
        meta,
        sql.Column('password_id', sql.String(64), primary_key=True,
                   nullable=False),
        sql.Column('identity_id', sql.String(64),
        sql.ForeignKey('identity.identity_id', ondelete='CASCADE')),
        sql.Column('user_name', sql.String(255), nullable=False),
        sql.Column('namespace', sql.String(64), nullable=False),
        sql.Column('password', sql.String(256), nullable=False),
        sql.Column('expires_at', sql.DateTime(), nullable=True))
    password_table.create(migrate_engine, checkfirst=True)
