#!/usr/bin/env python
from migrate.versioning.shell import main
main(url='sqlite:///keystone.db', debug='False', repository='keystone/backends/sqlalchemy/migrate_repo/')
