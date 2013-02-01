import sqlalchemy as sql
from keystone import config


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    tenant_table = sql.Table('tenant', meta, autoload=True)
    legacy_membership_table = sql.Table('user_tenant_membership',
                                        meta,
                                        autoload=True)
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
    insert = project_table.insert()
    for tenant in session.query(tenant_table).all():
        insert.execute(tenant)

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

    insert = user_project_membership_table.insert()
    for membership in session.query(legacy_membership_table).all():
        insert.execute(membership)
    legacy_membership_table.drop()
    tenant_table.drop()
    session.commit()
    session.close()


def downgrade(migrate_engine):
    """Replace API-version specific endpoint tables with one based on v2."""
    meta = sql.MetaData()
    meta.bind = migrate_engine
    project_table = sql.Table('project', meta, autoload=True)
    upgrade_membership_table = sql.Table('user_project_membership',
                                         meta,
                                         autoload=True)

    tenant_table = sql.Table(
        'tenant',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('name', sql.String(64), unique=True, nullable=False),
        sql.Column('extra', sql.Text()))
    tenant_table.create(migrate_engine, checkfirst=True)

    maker = sql.orm.sessionmaker(bind=migrate_engine)
    session = maker()
    insert = project_table.insert()

    for project in session.query(project_table).all():
        insert.execute(project)

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
            'insert into user_tenant_membership (user_id, tenant_id)'
            ' values (:user_id, :tenant_id)',
            membership)

    upgrade_membership_table.drop()
    project_table.drop()
    session.commit()
    session.close()
