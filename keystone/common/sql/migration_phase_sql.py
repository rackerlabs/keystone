# Copyright 2012 OpenStack Foundation
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

from keystone.common import sql
from keystone import exception

# We only support one row of status at the moment, so we define a key which we
# hide from the caller.
PHASE_STATUS_KEY = 'Status'


class MigratonPhaseModel(sql.ModelBase, sql.DictBase):
    __tablename__ = 'migration_phase'
    attributes = ['current_version', 'migrating_to_version', 'current_phase']
    status = sql.Column(sql.String(64), primary_key=True)
    current_version = sql.Column(sql.String(64), nullable=False)
    migrating_to_version = sql.Column(sql.String(64), nullable=False)
    current_phase = sql.Column(sql.String(64), nullable=False)

    @classmethod
    def from_dict(cls, d):
        new_d = d.copy()
        return cls(**new_d)

    def to_dict(self):
        """Return the model's attributes as a dictionary.

        Don't let the internal 'Status' key escape.

        """
        d = {}
        for attr in self.__class__.attributes:
            d[attr] = getattr(self, attr)
        return d


class MigratonPhase(object):

    @sql.handle_conflicts(conflict_type='migration_status')
    def create_migration_status(self, values):
        with sql.session_for_write() as session:
            ref = MigratonPhaseModel.from_dict(values)
            ref.status = PHASE_STATUS_KEY
            session.add(ref)
            return ref.to_dict()

    def get_migration_status(self):
        with sql.session_for_read() as session:
            ref = session.query(MigratonPhaseModel).get(PHASE_STATUS_KEY)
            return ref.to_dict()

    def update_migration_status(self, values):
        with sql.session_for_write() as session:
            ref = session.query(MigratonPhaseModel).get(PHASE_STATUS_KEY)
            if not ref:
                raise exception.NotFound(target='migration_status')
            old_dict = ref.to_dict()
            for k in values:
                old_dict[k] = values[k]
            new_phase_status = MigratonPhaseModel.from_dict(old_dict)
            for attr in MigratonPhaseModel.attributes:
                setattr(ref, attr, getattr(new_phase_status, attr))
            return ref.to_dict()

    # NOTE(henry-nash): There is no need to support List or Delete since we
    # currently only use a single row in the table, which is created on the
    # first ever migration and never needs to be remove.
