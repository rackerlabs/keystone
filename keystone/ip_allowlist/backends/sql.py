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

"""SQL backend for the IP allowlist driver."""

from keystone.common import sql
from keystone import exception
from keystone.ip_allowlist.backends import base


class IPAllowlistEntry(sql.ModelBase, sql.ModelDictMixin):
    __tablename__ = 'ip_allowlist_entry'
    attributes = ['id', 'user_id', 'cidr', 'description', 'created_at']

    id = sql.Column(sql.String(64), primary_key=True, nullable=False)
    user_id = sql.Column(sql.String(64), nullable=False, index=True)
    cidr = sql.Column(sql.String(64), nullable=False)
    description = sql.Column(sql.Text(), nullable=True)
    created_at = sql.Column(sql.DateTimeInt(), nullable=True)

    __table_args__ = (
        sql.UniqueConstraint(
            'user_id', 'cidr', name='uq_ip_allowlist_user_cidr'
        ),
    )


class IPAllowlist(base.IPAllowlistDriverBase):

    def list_allowed_cidrs(self, user_id):
        with sql.session_for_read() as session:
            query = session.query(IPAllowlistEntry).filter_by(
                user_id=user_id
            )
            return [entry.to_dict() for entry in query]

    def get_allowed_cidr(self, user_id, entry_id):
        with sql.session_for_read() as session:
            entry = session.query(IPAllowlistEntry).filter_by(
                id=entry_id, user_id=user_id
            ).first()
            if not entry:
                raise exception.IPAllowlistEntryNotFound(entry_id=entry_id)
            return entry.to_dict()

    @sql.handle_conflicts(conflict_type='ip_allowlist_entry')
    def create_allowed_cidr(self, user_id, entry_id, entry):
        ref = IPAllowlistEntry(
            id=entry_id,
            user_id=user_id,
            cidr=entry['cidr'],
            description=entry.get('description'),
            created_at=entry.get('created_at'),
        )
        with sql.session_for_write() as session:
            session.add(ref)
            return ref.to_dict()

    def delete_allowed_cidr(self, user_id, entry_id):
        with sql.session_for_write() as session:
            entry = session.query(IPAllowlistEntry).filter_by(
                id=entry_id, user_id=user_id
            ).first()
            if not entry:
                raise exception.IPAllowlistEntryNotFound(entry_id=entry_id)
            session.delete(entry)
