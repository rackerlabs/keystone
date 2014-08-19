# Copyright 2014 IBM Corp.
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

import uuid

from keystone.common import dependency
from keystone.common import sql
from keystone import exception
from keystone.i18n import _
from keystone.openstack.common import log

LOG = log.getLogger(__name__)
MAX_REGION_DEPTH = 50


class PolicyAssociation(sql.ModelBase, sql.ModelDictMixin):
    __tablename__ = 'policy_association'
    attributes = ['policy_id', 'endpoint_id', 'region_id', 'service_id']
    # The id column is never exposed outside this module. It only exists to
    # provide a prime key, given that the real columns we would like to use
    # (endpoint_id, service_id, region_id) can be null
    id = sql.Column(sql.String(64), primary_key=True)
    policy_id = sql.Column(sql.String(64), nullable=False)
    endpoint_id = sql.Column(sql.String(64))
    service_id = sql.Column(sql.String(64))
    region_id = sql.Column(sql.String(64))
    __table_args__ = (sql.UniqueConstraint('endpoint_id', 'service_id',
                                           'region_id'), {})

    def to_dict(self):
        """Returns the model's attributes as a dictionary.

        We override the standard method in order to hide the id column,
        since this only exists to provide the table with a prime key.

        """
        d = {}
        for attr in self.__class__.attributes:
            d[attr] = getattr(self, attr)
        return d


@dependency.requires('policy_api')
@dependency.requires('catalog_api')
class EndpointPolicy(object):

    def _assert_valid_association(self, endpoint_id, service_id, region_id):
        """Assert that the association is supported.

        There are three types of association supported:

        - Endpoint (in which case service and region must be None)
        - Service and region (in which endpoint must be None)
        - Service (in which case endpoint and region must be None)

        """
        if endpoint_id and service_id is None and region_id is None:
            return
        if (endpoint_id is None and
                service_id is not None and region_id is not None):
            return
        if (endpoint_id is None and region_id is None and
                service_id is not None):
            return

        raise exception.InvalidPolicyAssociation(endpoint_id=endpoint_id,
                                                 service_id=service_id,
                                                 region_id=region_id)

    @sql.handle_conflicts(conflict_type='policy_association')
    def create_policy_association(self, policy_id, endpoint_id=None,
                                  service_id=None, region_id=None):
        self._assert_valid_association(endpoint_id, service_id, region_id)
        try:
            with sql.transaction() as session:
                query = session.query(PolicyAssociation)
                query = query.filter_by(endpoint_id=endpoint_id)
                query = query.filter_by(service_id=service_id)
                query = query.filter_by(region_id=region_id)
                association = query.one()
                association.policy_id = policy_id
        except sql.NotFound:
            with sql.transaction() as session:
                association = PolicyAssociation(id=uuid.uuid4().hex,
                                                policy_id=policy_id,
                                                endpoint_id=endpoint_id,
                                                service_id=service_id,
                                                region_id=region_id)
                session.add(association)
                return

    def check_policy_association(self, policy_id, endpoint_id=None,
                                 service_id=None, region_id=None):
        self._assert_valid_association(endpoint_id, service_id, region_id)
        with sql.transaction() as session:
            query = session.query(PolicyAssociation)
            query = query.filter_by(policy_id=policy_id)
            query = query.filter_by(endpoint_id=endpoint_id)
            query = query.filter_by(service_id=service_id)
            query = query.filter_by(region_id=region_id)
            try:
                query.one()
            except sql.NotFound:
                raise exception.NotFound(_('Policy association Not Found'))

    def delete_policy_association(self, policy_id, endpoint_id=None,
                                  service_id=None, region_id=None):
        self._assert_valid_association(endpoint_id, service_id, region_id)
        with sql.transaction() as session:
            query = session.query(PolicyAssociation)
            query = query.filter_by(policy_id=policy_id)
            query = query.filter_by(endpoint_id=endpoint_id)
            query = query.filter_by(service_id=service_id)
            query = query.filter_by(region_id=region_id)
            query.delete()

    def list_endpoints_for_policy(self, policy_id):
        # TODO(henry-nash): Needs to be implemented
        raise exception.NotImplemented()

    def get_policy_for_endpoint(self, endpoint_id):

        def _get_policy(policy_id, endpoint_id):
            try:
                return self.policy_api.get_policy(policy_id)
            except exception.PolicyNotFound:
                msg = _('Policy entity %(policy_id)s referenced in '
                        'association for endpoint %(endpoint_id)s not found.')
                LOG.warning(msg, {'policy_id': policy_id,
                                  'endpoint_id': endpoint_id})
                raise

        # First let's see if there is a policy explicitly defined for
        # this endpoint.

        with sql.transaction() as session:
            query = session.query(PolicyAssociation)
            query = query.filter_by(endpoint_id=endpoint_id)
            try:
                ref = query.one()
                return _get_policy(ref.policy_id, endpoint_id)
            except sql.NotFound:
                pass

        # So there wasn't a policy explicitly defined for this endpoint, so
        # now let's see if there is one for the Region & Service.

        endpoint = self.catalog_api.get_endpoint(endpoint_id)
        service = self.catalog_api.get_service(endpoint['service_id'])
        # TODO(henry-nash): The following should reference region_id once the
        # change to migrate from region -> region_id is in.
        if endpoint.get('region', None) is not None:
            next_region_id = endpoint['region']
            first_region_id = next_region_id
            iteration_count = 0
            while next_region_id is not None:
                with sql.transaction() as session:
                    query = session.query(PolicyAssociation)
                    query = query.filter_by(service_id=service['id'])
                    query = query.filter_by(region_id=next_region_id)
                    try:
                        ref = query.one()
                        return _get_policy(ref.policy_id, endpoint_id)
                    except sql.NotFound:
                        pass
                # There wasn't one for that region  & service, let's
                # chase up the region tree
                region = self.catalog_api.get_region(next_region_id)
                next_region_id = None
                if region.get('parent_region_id', None) is not None:
                    next_region_id = region['parent_region_id']
                    iteration_count += 1
                    if iteration_count > MAX_REGION_DEPTH:
                        msg = _('Region tree starting at %(region_id)s has '
                                'exceeded height of %(height)s - abandoning '
                                'region policy search.')
                        LOG.error(msg, {'region_id': first_region_id,
                                        'height': MAX_REGION_DEPTH})
                        break

        # Finally, just check if there is one for the Service.
        with sql.transaction() as session:
            query = session.query(PolicyAssociation)
            query = query.filter_by(service_id=service['id'])
            query = query.filter_by(region_id=None)
            try:
                ref = query.one()
                return _get_policy(ref.policy_id, endpoint_id)
            except sql.NotFound:
                pass

        msg = (_('No policy is associated with endpoint '
                 '%(endpoint_id)s.') % {'endpoint_id': endpoint_id})
        raise exception.NotFound(msg)
