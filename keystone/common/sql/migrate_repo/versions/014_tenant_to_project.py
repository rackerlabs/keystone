import sqlalchemy as sql


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    legacy_table = sql.Table('tenant', meta, autoload=True)
    legacy_table.rename('project')


def downgrade(migrate_engine):
    """Replace API-version specific endpoint tables with one based on v2."""
    meta = sql.MetaData()
    meta.bind = migrate_engine
    legacy_table = sql.Table('project', meta, autoload=True)
    legacy_table.rename('tenant')
