# Copyright 2016 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import datetime

from keystone.auth.backends import base
from keystone.auth.backends import sql_model as model
from keystone.common import sql


class Auth(base.AuthDriverV8):

    def list_auth_attempts(self, user_id):
        with sql.session_for_read() as session:
            query = session.query(model.FailedAuthAttempts)
            query = query.filter_by(user_id=user_id)
            return [item.to_dict() for item in query]

    def reset_auth_attempts(self, user_id):
        with sql.session_for_write() as session:
            query = session.query(model.FailedAuthAttempts)
            query.filter_by(user_id=user_id).delete()

    def register_failed_auth_attempt(self, user_id):
        with sql.session_for_write() as session:
            session.add(
                model.FailedAuthAttempts.from_dict(dict(
                    user_id=user_id,
                    timestamp=datetime.datetime.now())
                )
            )
