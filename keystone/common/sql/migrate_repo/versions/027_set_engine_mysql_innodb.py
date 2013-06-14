
from sqlalchemy import MetaData


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine;
    # bind migrate_engine to your metadata

    tables = [
        'credential',
        'domain',
        'ec2_credential',
        'endpoint',
        'group',
        'group_domain_metadata',
        'group_project_metadata',
        'migrate_version',
        'policy',
        'project',
        'role',
        'service',
        'token',
        'trust',
        'trust_role',
        'user',
        'user_domain_metadata',
        'user_group_membership',
        'user_project_metadata',
    ]

    meta = MetaData()
    meta.bind = migrate_engine
    if migrate_engine.name == "mysql":
        d = migrate_engine.execute("SHOW TABLE STATUS WHERE Engine!='InnoDB';")
        for row in d.fetchall():
            table_name = row[0]
            if table_name in tables:
                migrate_engine.execute("ALTER TABLE %s Engine=InnoDB" %
                                       table_name)


def downgrade(migrate_engine):
    pass
