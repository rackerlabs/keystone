# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import shutil

import fixtures

from keystone.common import sql
from keystone.common.sql import migration_helpers
from keystone import config
from keystone.openstack.common.db.sqlalchemy import migration
from keystone import tests


CONF = config.CONF


def _setup_database(extensions=None):
    if CONF.database.connection != tests.IN_MEM_DB_CONN_STRING:
        db = tests.dirs.tmp('test.db')
        pristine = tests.dirs.tmp('test.db.pristine')

        if os.path.exists(db):
            os.unlink(db)
        if not os.path.exists(pristine):
            migration.db_sync(sql.get_engine(),
                              migration_helpers.find_migrate_repo())
            for extension in (extensions or []):
                migration_helpers.sync_database_to_version(extension=extension)
            shutil.copyfile(db, pristine)
        else:
            shutil.copyfile(pristine, db)


def _find_and_import_sql_modules(start):
    for root, dirs, files in os.walk(start):
        if root.endswith('backends') and 'sql.py' in files:
            module_name = root.replace(os.sep, '.') + '.sql'
            __import__(module_name)


class Database(fixtures.Fixture):
    """A fixture for setting up and tearing down a database.

    """

    def __init__(self, extensions=None):
        super(Database, self).__init__()
        self._extensions = extensions
        keystone_root = os.path.normpath(os.path.join(
            os.path.dirname(__file__), '..', '..'))
        _find_and_import_sql_modules(keystone_root)

    def setUp(self):
        super(Database, self).setUp()
        _setup_database(extensions=self._extensions)

        self.engine = sql.get_engine()
        sql.ModelBase.metadata.create_all(bind=self.engine)
        self.addCleanup(sql.cleanup)
        self.addCleanup(sql.ModelBase.metadata.drop_all, bind=self.engine)
