import sqlalchemy as sql


def base_index(meng):
    """ Prep the model for Token Table """
    meta = sql.MetaData()
    meta.bind = meng
    token = sql.Table('token', meta, autoload=True)
    idx = sql.Index('ix_token_valid', token.c.valid)
    return idx


def upgrade(migrate_engine):
    """ Add Index for Token Valid """
    idx = base_index(meng=migrate_engine)
    idx.create(migrate_engine)


def downgrade(migrate_engine):
    """ Remove Index for Token Valid """
    idx = base_index(meng=migrate_engine)
    idx.drop(migrate_engine)
