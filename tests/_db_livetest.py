# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import subprocess

from keystone import config
from keystone import test
from migrate.versioning import api as versioning_api
import sqlalchemy
from sqlalchemy.orm import sessionmaker

from keystone.common import sql
from keystone import config
from keystone import test
from keystone.common.sql import migration
from sqlalchemy.orm import sessionmaker

import test_sql_upgrade

CONF = config.CONF


class SqlLiveUpgradeTests(test_sql_upgrade.SqlUpgradeTests):
    def do_config(self):
        self.config([test.etcdir('keystone.conf.sample'),
                     test.testsdir('test_overrides.conf'),
                     test.testsdir('backend_livesql.conf')])
        self.engine = sql.Base().get_engine(allow_global_engine=False)
        self.metadata = sqlalchemy.MetaData()
        maker = sessionmaker(bind=self.engine)
        session = maker()
        session.execute("drop database keystone")
        session.execute("create database keystone")
        session.commit()

    def setUp(self):
        super(SqlLiveUpgradeTests, self).setUp()
        
