import migrate

from migrate.changeset import constraint
from sqlalchemy import *


def upgrade(migrate_engine):
    meta = MetaData(bind=migrate_engine)
    role = Table('role', meta, autoload=True)
    service = Table('service', meta, autoload=True)
    service_id = Column('service_id', String(64), ForeignKey('service.id'))
    service_id.create(role)
    cons = constraint.UniqueConstraint(role.c.name, role.c.service_id)
    cons.create()


def downgrade(migrate_engine):
    meta = MetaData(bind=migrate_engine)
    role = Table('role', meta, autoload=True)
    cons = constraint.UniqueConstraint(role.c.name, role.c.service_id)
    try:
        cons.drop()
    except migrate.exceptions.NotSupportedError, e:
        if migrate_engine.name == 'sqlite':
            # not much we can do here
            print 'WARNING: can drop unique contraint name_service_id ' \
                ' from role table'
        else:
            raise e
    role.c.service_id.drop()
