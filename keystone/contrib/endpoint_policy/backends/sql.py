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

    def _assert_valid_association(self, policy_id, endpoint_id,
                                  service_id, region_id):
        """Assert that the association is supported.

        There are three types of association supported:

        - Endpoint (in which case service and region must be None)
        - Service and region (in which endpoint must be None)
        - Service (in which case endpoint and region must be None)

        """
        self.policy_api.get_policy(policy_id)
        if (endpoint_id is not None and
                service_id is None and region_id is None):
            self.catalog_api.get_endpoint(endpoint_id)
            return
        if (service_id is not None and region_id is not None and
                endpoint_id is None):
            self.catalog_api.get_service(service_id)
            self.catalog_api.get_region(region_id)
            return
        if (service_id is not None and
                endpoint_id is None and region_id is None):
            self.catalog_api.get_service(service_id)
            return

        raise exception.InvalidPolicyAssociation(endpoint_id=endpoint_id,
                                                 service_id=service_id,
                                                 region_id=region_id)

    @sql.handle_conflicts(conflict_type='policy_association')
    def create_policy_association(self, policy_id, endpoint_id=None,
                                  service_id=None, region_id=None):
        self._assert_valid_association(policy_id, endpoint_id,
                                       service_id, region_id)
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
        self._assert_valid_association(policy_id, endpoint_id,
                                       service_id, region_id)
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
        self._assert_valid_association(policy_id, endpoint_id,
                                       service_id, region_id)
        with sql.transaction() as session:
            query = session.query(PolicyAssociation)
            query = query.filter_by(policy_id=policy_id)
            query = query.filter_by(endpoint_id=endpoint_id)
            query = query.filter_by(service_id=service_id)
            query = query.filter_by(region_id=region_id)
            query.delete()

    def list_endpoints_for_policy(self, policy_id):

        def _get_endpoint(endpoint_id, policy_id):
            try:
                return self.catalog_api.get_endpoint(endpoint_id)
            except exception.EndpointNotFound:
                msg = _('Endpoint %(endpoint_id)s referenced in '
                        'association for policy %(policy_id)s not found.')
                LOG.warning(msg, {'policy_id': policy_id,
                                  'endpoint_id': endpoint_id})
                raise

        def _get_endpoints_for_service(service_id, endpoints):
            # TODO(henry-nash): Consider optimizing this in the future by
            # adding an explicit list_endpoints_for_service to the catalog API.
            return [ep for ep in endpoints if ep['service_id'] == service_id]

        def _get_endpoints_for_service_and_region(
                service_id, region_id, endpoints, regions):
            # TODO(henry-nash): Consider optimizing this in the future.
            # The lack of a two-way pointer in the region tree structure
            # makes this somewhat inefficient.

            def _recursively_get_endpoints_for_region(
                region_id, service_id, endpoint_list, region_list,
                    endpoints_found, regions_examined):
                """Recursively search down a region tree for endpoints.

                :param region_id: the point in the tree to examine
                :param service_id: the service we are interested in
                :param endpoint_list: list of all endpoints
                :param region_list: list of all regions
                :param endpoints_found: list of matching endpoints found so
                                        far - which will be updated if more are
                                        found in this iteration
                :param regions_examined: list of regions we have already looked
                                         at - used to spot illegal circular
                                         references in the tree to avoid never
                                         completing search
                :returns: None

                """

                if region_id in regions_examined:
                    msg = _('Circular reference or a repeated entry found in '
                            'region tree - %(policy_id)s.')
                    LOG.error(msg, {'region_id': ref.region_id})
                    return

                regions_examined.append(region_id)
                endpoints_found += (
                    [ep for ep in endpoint_list if
                     ep['service_id'] == service_id and
                     ep['region'] == region_id])

                for region in region_list:
                    if region['parent_region_id'] == region_id:
                        _recursively_get_endpoints_for_region(
                            region['id'], service_id, endpoints, regions,
                            endpoints_found, regions_examined)

            endpoints_found = []
            regions_examined = []

            # Now walk down the region tree
            _recursively_get_endpoints_for_region(
                region_id, service_id, endpoints, regions,
                endpoints_found, regions_examined)

            return endpoints_found

        matching_endpoints = []
        endpoints = self.catalog_api.list_endpoints()
        regions = self.catalog_api.list_regions()
        with sql.transaction() as session:
            query = session.query(PolicyAssociation)
            query = query.filter_by(policy_id=policy_id)
            refs = query.all()
            for ref in refs:
                if ref.endpoint_id is not None:
                    matching_endpoints.append(
                        _get_endpoint(ref.endpoint_id, policy_id))
                    continue

                if ref.service_id is not None and ref.region_id is None:
                    matching_endpoints += _get_endpoints_for_service(
                        ref.service_id, endpoints)
                    continue

                if ref.service_id is not None and ref.region_id is not None:
                    matching_endpoints += (
                        _get_endpoints_for_service_and_region(
                            ref.service_id, ref.region_id, endpoints, regions))
                    continue

                msg = _('Unsupported policy association found - '
                        'Policy %(policy_id)s, Endpoint %(endpoint_id)s, '
                        'Service %(service_id)s, Region %(region_id)s, ')
                LOG.warning(msg, {'policy_id': policy_id,
                                  'endpoint_id': ref.endpoint_id,
                                  'service_id': ref.service_id,
                                  'region_id': ref.region_id})
        return matching_endpoints

    def get_policy_for_endpoint(self, endpoint_id):

        def _get_policy(policy_id, endpoint_id):
            try:
                return self.policy_api.get_policy(policy_id)
            except exception.PolicyNotFound:
                msg = _('Policy %(policy_id)s referenced in '
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
            regions_examined = []
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
                regions_examined.append(next_region_id)
                region = self.catalog_api.get_region(next_region_id)
                next_region_id = None
                if region.get('parent_region_id', None) is not None:
                    next_region_id = region['parent_region_id']
                    if next_region_id in regions_examined:
                        msg = _('Circular reference or a repeated entry found '
                                'in region tree - %(policy_id)s.')
                        LOG.error(msg, {'region_id': next_region_id})
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
