from sqlalchemy import *
from migrate import *


def upgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine
    token = Table('token', meta, autoload=True)
    idx = Index('ix_token_valid', token.c.valid)
    idx.create(migrate_engine)
    idx = Index('ix_token_expires', token.c.expires)
    idx.create(migrate_engine)


def downgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine
    token = Table('token', meta, autoload=True)
    idx = Index('ix_token_valid', token.c.valid)
    idx.drop(migrate_engine)
    idx = Index('ix_token_expires', token.c.expires)
    idx.drop(migrate_engine)
