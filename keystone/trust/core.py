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

"""Main entry point into the Identity service."""

import abc

import six

from keystone.common import dependency
from keystone.common import manager
from keystone import config
from keystone import exception
from keystone.i18n import _
from keystone import notifications
from keystone.openstack.common import log


CONF = config.CONF

LOG = log.getLogger(__name__)


@dependency.provider('trust_api')
class Manager(manager.Manager):
    """Default pivot point for the Trust backend.

    See :mod:`keystone.common.manager.Manager` for more details on how this
    dynamically calls the backend.

    """
    _TRUST = "OS-TRUST:trust"

    def __init__(self):
        super(Manager, self).__init__(CONF.trust.driver)

    @staticmethod
    def _validate_trust(trust):
        # Validate against:
        # * remaining_uses is int and >=0 if any
        #   and allow_redelegation is not set
        if trust.setdefault('remaining_uses', None) is not None:
            if (trust['remaining_uses'] <= 0 or
                    not isinstance(trust['remaining_uses'], int) or
                    trust.get('allow_redelegation')):
                msg = _('remaining_uses must be a positive integer or null.')
                raise exception.ValidationError(msg)
        # * 0 < redelegation_count <= max_redelegation_count if any
        #   and allow_redelegation is set
        if trust.get('allow_redelegation'):
            max_redelegation_count = CONF.trust.max_redelegation_count
            redelegation_count = trust.get('redelegation_count')
            if (redelegation_count and not
                    (0 < redelegation_count <= max_redelegation_count)):
                raise exception.Forbidden(
                    _('Requested redelegation depth of %(redelegation_count)d'
                      ' out of allowed range of [0..%(max_count)d]'),
                    redelegation_count=redelegation_count,
                    max_count=max_redelegation_count)

    @staticmethod
    def _validate_redelegation(redelegated_trust, trust):
        # Validate against:
        # * allow_redelegation
        if (not redelegated_trust.get('allow_redelegation')
                or not CONF.trust.allow_redelegation):
            raise exception.Forbidden(
                _('Redelegation is not allowed'))

        # * f0 < redelegation_count <= max_redelegation_count
        max_redelegation_count = CONF.trust.max_redelegation_count
        redelegation_depth = redelegated_trust.get('redelegation_count', 0)
        if not (0 < redelegation_depth <= max_redelegation_count):
            raise exception.Forbidden(
                _('Remaining redelegation depth of %(redelegation_depth)d'
                  ' out of allowed range of [0..%(max_count)d]'),
                redelegation_depth=redelegation_depth,
                max_count=max_redelegation_count)

        # * remaining_uses is None
        if trust.get('remaining_uses') is not None:
            raise exception.Forbidden(
                _('Field "remaining_uses" is set to %(value)s'
                  ' while it must not be set in order to redelegate a trust'),
                value=trust.get('remaining_uses'))

        # * expiry times
        trust_expiry = trust.get('expires_at')
        redelegated_expiry = redelegated_trust['expires_at']
        if trust_expiry:
            if redelegated_expiry < trust_expiry.replace(tzinfo=None):
                raise exception.Forbidden(
                    _('Requested expiration time is more '
                      'than redelegated trust can provide'))
        else:
            trust['expires_at'] = redelegated_expiry

        # * role subset
        parent_roles = set(role['id']
                           for role in redelegated_trust['roles'])
        if not all(role['id'] in parent_roles for role in trust['roles']):
            raise exception.Forbidden(
                _('Some of requested roles are not in redelegated trust'))

    def get_trust_pedigree(self, trust_id):
        trust = self.driver.get_trust(trust_id)
        trust_chain = [trust]
        if trust and trust.get('redelegated_trust_id'):
            trusts = self.driver.list_trusts_for_trustor(
                trust['trustor_user_id'])
            while trust_chain[-1].get('redelegated_trust_id'):
                for t in trusts:
                    if t['id'] == trust_chain[-1]['redelegated_trust_id']:
                        trust_chain.append(t)
                        break

        return trust_chain

    def get_trust(self, trust_id, deleted=False):
        trust = self.driver.get_trust(trust_id, deleted)

        if trust and trust.get('redelegated_trust_id') and not deleted:
            trust_chain = self.get_trust_pedigree(trust_id)

            for parent, child in zip(trust_chain[1:], trust_chain):
                self._validate_redelegation(parent, child)

        return trust

    @notifications.created(_TRUST)
    def create_trust(self, trust_id, trust, roles, redelegated_trust=None):
        """Create a new trust.

        :returns: a new trust
        """
        if redelegated_trust:
            # Error on attempt to redelegate using non-redelegable trust
            if not redelegated_trust.get('allow_redelegation'):
                msg = _('Redelegation of non-redelegable trust is forbidden')
                raise exception.Forbidden(msg)

            # Populate trust with:
            # * redelegation_count - 1
            remaining_depth = redelegated_trust.get('redelegation_count') - 1
            requested_depth = trust.setdefault(
                'redelegation_count', remaining_depth)
            # * redelegated_trust_id
            trust['redelegated_trust_id'] = redelegated_trust['id']

            # Check whether agent leave redelegation_count intact
            if remaining_depth != requested_depth:
                msg = _('Modifying redelegation_count upon redelegation '
                        'is forbidden. Omitting this parameter is advised.')
                raise exception.Forbidden(msg)

            # Check entire trust pedigree validity
            pedigree = self.get_trust_pedigree(redelegated_trust['id'])
            for t in pedigree:
                self._validate_redelegation(t, trust)
        elif trust.get('allow_redelegation'):
            # Default for initial trust in chain is max_redelegation_count
            trust.setdefault('redelegation_count',
                             CONF.trust.max_redelegation_count)

        self._validate_trust(trust)

        return self.driver.create_trust(trust_id, trust, roles)

    @notifications.deleted(_TRUST)
    def delete_trust(self, trust_id):
        """Remove a trust.

        :raises: keystone.exception.TrustNotFound
        """
        trust = self.driver.get_trust(trust_id)
        if not trust:
            raise exception.TrustNotFound(trust_id)

        trusts = self.driver.list_trusts_for_trustor(
            trust['trustor_user_id'])

        for t in trusts:
            if t.get('redelegated_trust_id') == trust_id:
                # recursive call to make sure all notifications are sent
                try:
                    self.delete_trust(t['id'])
                except exception.TrustNotFound:
                    # if trust was deleted by concurrent process
                    # consistency must not suffer
                    pass

        # end recursion
        self.driver.delete_trust(trust_id)


@six.add_metaclass(abc.ABCMeta)
class Driver(object):

    @abc.abstractmethod
    def create_trust(self, trust_id, trust, roles):
        """Create a new trust.

        :returns: a new trust
        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def get_trust(self, trust_id, deleted=False):
        """Get a trust by the trust id.

        :param trust_id: the trust identifier
        :type trust_id: string
        :param deleted: return the trust even if it is deleted, expired, or
                        has no consumptions left
        :type deleted: bool
        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def list_trusts(self):
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def list_trusts_for_trustee(self, trustee):
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def list_trusts_for_trustor(self, trustor):
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def delete_trust(self, trust_id):
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def consume_use(self, trust_id):
        """Consume one use when a trust was created with a limitation on its
        uses, provided there are still uses available.

        :raises: keystone.exception.TrustUseLimitReached,
                 keystone.exception.TrustNotFound
        """
        raise exception.NotImplemented()  # pragma: no cover
