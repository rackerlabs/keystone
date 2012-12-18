import sqlalchemy as sql
from sqlalchemy.orm import sessionmaker


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    user = sql.Table('user', meta, autoload=True)
    user.c.name.alter(type=sql.String(128))


def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    user = sql.Table('user', meta, autoload=True)
    user.c.name.alter(type=sql.String(64))
