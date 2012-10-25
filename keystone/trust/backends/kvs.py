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
"""
An in memory implementation of the trusts API.
only to be used for testing purposes
"""
import copy
import datetime


from keystone.common import kvs
from keystone.openstack.common import timeutils
from keystone import exception
from keystone import trust


class Trust(kvs.Base, trust.Driver):
    def create_trust(self, trust_id, trustor, trustee, tenant, roles,
                     endpoints):

        trust_ref = {}
        trust_ref['id'] = trust_id
        trust_ref['trustor'] = trustor
        trust_ref['trustee'] = trustee
        trust_ref['tenant_id'] = tenant
        trust_ref['extra'] = {}

        added_roles = []
        for role in roles:
            trust_role = {'role_id': role}
            added_roles.append(role)
        trust_ref['roles'] = added_roles

        added_endpoints = []
        for endpoint in endpoints:
            trust_endpoint = {'endpoint_id': endpoint}
            added_endpoints.append(endpoint)
        trust_ref['endpoints'] = added_endpoints

        self.db.set('trust-%s' % trust_id, trust_ref)
        return copy.deepcopy(trust_ref)

    def get_trust(self, trust_id):
        try:
            ref = self.db.get('trust-%s' % trust_id)
        except exception.NotFound:
            raise exception.TrustNotFound(trust_id=trust_id)
        return copy.deepcopy(ref)

    def delete_trust(self, trust_id):
        try:
            ref = self.db.get('trust-%s' % trust_id)
        except exception.NotFound:
            raise exception.TrustNotFound(token_id=token_id)
        self.db.delete('trust-%s' % trust_id)
