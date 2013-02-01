import sqlalchemy as sql
from keystone import config

def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    tenant_table = sql.Table('tenant', meta, autoload=True)
    legacy_membership_table = sql.Table('user_tenant_membership', meta, autoload=True)
    project_table = sql.Table(
    'project',
    meta,
    sql.Column('id', sql.String(64), primary_key=True),
    sql.Column('name', sql.String(64), unique=True, nullable=False),
    sql.Column('description', sql.String(64), unique=False, nullable=True),
    sql.Column('enabled', sql.types.Boolean, default=True),
    sql.Column('extra', sql.Text()))
    project_table.create(migrate_engine, checkfirst=True)
    maker = sql.orm.sessionmaker(bind=migrate_engine)
    session = maker()
    for tenant in session.query(tenant_table).all():
        session.execute(
        'insert into project (id, name, extra, description, enabled) values (:id, :name, :extra, :description, :enabled)',
        tenant)

    user_project_membership_table = sql.Table(
    'user_project_membership',
    meta,
    sql.Column(
        'user_id',
        sql.String(64),
        sql.ForeignKey('user.id'),
        primary_key=True),
    sql.Column(
        'project_id',
        sql.String(64),
        sql.ForeignKey('project.id'),
        primary_key=True))
    user_project_membership_table.create(migrate_engine, checkfirst=True)

    for membership in session.query(legacy_membership_table).all():
        session.execute(
        'insert into user_project_membership (user_id, project_id) values (:user_id, :project_id)',
        membership)
    session.execute("drop table user_tenant_membership")
    session.execute("drop table tenant")
    session.commit()
    session.close()


def downgrade(migrate_engine):
    """Replace API-version specific endpoint tables with one based on v2."""
    meta = sql.MetaData()
    meta.bind = migrate_engine
    project_table = sql.Table('project', meta, autoload=True)
    upgrade_membership_table = sql.Table('user_project_membership', meta, autoload=True)

    tenant_table = sql.Table(
    'tenant',
    meta,
    sql.Column('id', sql.String(64), primary_key=True),
    sql.Column('name', sql.String(64), unique=True, nullable=False),
    sql.Column('extra', sql.Text()))
    tenant_table.create(migrate_engine, checkfirst=True)

    maker = sql.orm.sessionmaker(bind=migrate_engine)
    session = maker()
    for tenant in session.query(tenant_table).all():
        session.execute(
        'insert into tenant (id, name, extra) values (:id, :name, :extra)',
        tenant)

    user_tenant_membership_table = sql.Table(
    'user_tenant_membership',
    meta,
    sql.Column(
        'user_id',
        sql.String(64),
        sql.ForeignKey('user.id'),
        primary_key=True),
    sql.Column(
        'tenant_id',
        sql.String(64),
        sql.ForeignKey('tenant.id'),
        primary_key=True))
    user_tenant_membership_table.create(migrate_engine, checkfirst=True)

    for membership in session.query(upgrade_membership_table).all():
        session.execute(
        'insert into user_tenant_membership (user_id, tenant_id) values (:user_id, :tenant_id)',
        membership)

    session.execute("drop table user_project_membership")
    session.execute("drop table project")
    session.commit()
    session.close()

