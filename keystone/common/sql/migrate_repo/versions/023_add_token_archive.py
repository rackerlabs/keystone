
import sqlalchemy as sql


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    table = sql.Table(
        'token_archive',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('expires', sql.DateTime()),
        sql.Column('extra', sql.Text()),
        sql.Column('valid', sql.Boolean(), default=True, nullable=False),
        sql.Column('trust_id', sql.String(64), nullable=True),
        sql.Column('user_id', sql.String(64), nullable=True))
    table.create(migrate_engine, checkfirst=True)


def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    table = sql.Table('token_archive', meta, autoload=True)
    table.drop(migrate_engine, checkfirst=True)
