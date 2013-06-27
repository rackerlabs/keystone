import sqlalchemy as sql


def base_index(meng):
    """ Prep the model for Token Table """
    meta = sql.MetaData()
    meta.bind = meng
    token = sql.Table('token', meta, autoload=True)
    idx = sql.Index('ix_token_expires', token.c.expires)
    return idx


def upgrade(migrate_engine):
    """ Add index for token expires """
    idx = base_index(meng=migrate_engine)
    idx.create(migrate_engine)


def downgrade(migrate_engine):
    """ Remove index for Token Expires """
    idx = base_index(meng=migrate_engine)
    idx.drop(migrate_engine)
