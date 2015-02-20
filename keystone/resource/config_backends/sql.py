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


class WhiteListedConfig(sql.ModelBase, sql.ModelDictMixin):
    __tablename__ = 'whitelisted_config'
    domain_id = sql.Column(sql.String(64), primary_key=True)
    config = sql.Column(sql.JsonBlob(), nullable=False)


class SensitiveConfig(sql.ModelBase, sql.ModelDictMixin):
    __tablename__ = 'sensitive_config'
    domain_id = sql.Column(sql.String(64), primary_key=True)
    group = sql.Column(sql.String(255), nullable=False)
    option = sql.Column(sql.String(255), nullable=False)
    value = sql.Column(sql.String(255), nullable=False)
    __table_args__ = (sql.UniqueConstraint('domain_id', 'group',
                                           'option'), {})


class DomainConfig(resource.DomainConfigDriver):

    @sql.handle_conflicts(conflict_type='domain_config')
    def create_config(self, domain_id, config):
        with sql.transaction() as session:
            ref = WhiteListedConfig(domain_id=domain_id, config=config)
            session.add(ref)
            return config

    def _get_config(self, session, domain_id):
        ref = session.query(WhiteListedConfig).get(domain_id)
        if not ref:
            raise exception.DomainConfigNotFound(domain_id=domain_id)
        return ref

    def get_config(self, domain_id):
        with sql.transaction() as session:
            return self._get_config(session, domain_id).config

    def update_config(self, domain_id, config):
        with sql.transaction() as session:
            ref = self._get_config(session, domain_id)
            ref.config = config
            return config

    def delete_config(self, domain_id):
        with sql.transaction() as session:
            ref = self._get_config(session, domain_id)
            session.delete(ref)

    @sql.handle_conflicts(conflict_type='sensitive_config')
    def create_sensitive_config_option(self, domain_id, group, option, value):
        with sql.transaction() as session:
            ref = SensitiveConfig(domain_id=domain_id, group=group,
                                  option=option, value=value)
            session.add(ref)
            ret_ref = ref.to_dict()
            ret_ref.pop('domain_id')
            return ret_ref

    def _get_sensitive_config_option(self, session, domain_id, group, option):
        try:
            ref = (session.query(SensitiveConfig).
                   filter_by(domain_id=domain_id, group=group,
                             option=option).one())
        except sql.NotFound:
            raise exception.DomainConfigNotFound(domain_id=domain_id)
        return ref

    def get_sensitive_config_option(self, domain_id, group, option):
        with sql.transaction() as session:
            ref = self._get_sensitive_config_option(session, domain_id,
                                                    group, option)
            ret_ref = ref.to_dict()
            ret_ref.pop('domain_id')
            return ret_ref

    def update_sensitive_config_option(self, domain_id, group, option, value):
        with sql.transaction() as session:
            ref = self._get_sensitive_config_option(session, domain_id,
                                                    group, option)
            ref.value = value
            ret_ref = ref.to_dict()
            ret_ref.pop('domain_id')
            return ret_ref

    def delete_sensitive_config_option(self, domain_id, group, option):
        with sql.transaction() as session:
            ref = self._get_sensitive_config_option(session, domain_id,
                                                    group, option)
            session.delete(ref)
