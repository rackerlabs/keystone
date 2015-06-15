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

from keystone.common import sql
from keystone import exception
from keystone import resource


SQL_MUTEX = 'SQL'


class ConfigMutex(sql.ModelBase, sql.ModelDictMixin):
    __tablename__ = 'config_mutex'
    mutex = sql.Column(sql.String(64), primary_key=True)
    domain_id = sql.Column(sql.String(64), nullable=False)


class DomainConfig(resource.config_backends.sql.DomainConfig):

    def obtain_config_sql_mutex(self, domain_id):
        try:
            with sql.transaction() as session:
                ref = ConfigMutex(mutex=SQL_MUTEX, domain_id=domain_id)
                session.add(ref)
            return True
        except sql.DBDuplicateEntry:
            pass
        return False

    def read_config_sql_mutex(self):
        with sql.transaction() as session:
            ref = session.query(ConfigMutex).get(SQL_MUTEX)
            if not ref:
                raise exception.ConfigSQLMutexNotFound()
        return ref.domain_id

    def free_config_sql_mutex(self, domain_id):
        """Silently delete any mutex for the domain specified."""

        with sql.transaction() as session:
            query = session.query(ConfigMutex)
            query = query.filter_by(mutex=SQL_MUTEX)
            query = query.filter_by(domain_id=domain_id)
            query.delete(False)
