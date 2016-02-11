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

import uuid

from keystone.common import sql
from keystone import exception
from keystone import identity
from keystone.identity.backends.sql import FederatedIdentity
from keystone.identity.backends.sql import Password
from keystone.identity.backends.sql import User
from keystone.identity.backends.sql import UserIdentity


class ShadowUsers(identity.ShadowUsersDriverV8):
    @sql.handle_conflicts(conflict_type='federated_identity')
    def create_federated_user(self, federated_dict, user_id=None):
        user = {
            'id': uuid.uuid4().hex,
            'enabled': True
        }
        session = sql.get_session()
        with session.begin():
            federated_ref = FederatedIdentity.from_dict(federated_dict, False)
            user_ref = UserIdentity.from_dict(user)
            user_ref.federated_identities.append(federated_ref)
            session.add(user_ref)
        return identity.filter_user(user_ref.to_dict())

    def get_federated_user(self, idp_id, unique_id):
        session = sql.get_session()
        query = session.query(UserIdentity).outerjoin(User).outerjoin(Password)
        query = query.join(FederatedIdentity)
        query = query.filter(FederatedIdentity.idp_id == idp_id)
        query = query.filter(FederatedIdentity.unique_id == unique_id)
        try:
            user_ref = query.one()
        except sql.NotFound:
            raise exception.UserNotFound(user_id=unique_id)
        return identity.filter_user(user_ref.to_dict())
