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

"""Main entry point into the Revoke service."""

import abc
import datetime

from oslo_config import cfg
from oslo_utils import timeutils
import six

from keystone.common import cache
from keystone.common import dependency
from keystone.common import extension
from keystone.common import manager
from keystone import exception
from keystone.i18n import _
from keystone.models import revoke_model
from keystone import notifications


CONF = cfg.CONF


EXTENSION_DATA = {
    'name': 'OpenStack Revoke API',
    'namespace': 'http://docs.openstack.org/identity/api/ext/'
                 'OS-REVOKE/v1.0',
    'alias': 'OS-REVOKE',
    'updated': '2014-02-24T20:51:0-00:00',
    'description': 'OpenStack revoked token reporting mechanism.',
    'links': [
        {
            'rel': 'describedby',
            'type': 'text/html',
            'href': 'http://specs.openstack.org/openstack/keystone-specs/api/'
                    'v3/identity-api-v3-os-revoke-ext.html',
        }
    ]}
extension.register_admin_extension(EXTENSION_DATA['alias'], EXTENSION_DATA)
extension.register_public_extension(EXTENSION_DATA['alias'], EXTENSION_DATA)

MEMOIZE = cache.get_memoization_decorator(group='revoke')


def revoked_before_cutoff_time():
    expire_delta = datetime.timedelta(
        seconds=CONF.token.expiration + CONF.revoke.expiration_buffer)
    oldest = timeutils.utcnow() - expire_delta
    return oldest


@dependency.provider('revoke_api')
class Manager(manager.Manager):
    """Default pivot point for the Revoke backend.

    Performs common logic for recording revocations.

    See :mod:`keystone.common.manager.Manager` for more details on
    how this dynamically calls the backend.

    """

    driver_namespace = 'keystone.revoke'

    def __init__(self):
        super(Manager, self).__init__(CONF.revoke.driver)
        self._register_listeners()
        self.model = revoke_model

    def _user_callback(self, service, resource_type, operation,
                       payload):
        self.revoke_by_user(payload['resource_info'])

    def _register_listeners(self):
        callbacks = {
            notifications.ACTIONS.internal: [
                [notifications.INVALIDATE_USER_TOKEN_PERSISTENCE,
                 self._user_callback],
            ]
        }

        for event, cb_info in callbacks.items():
            for resource_type, callback_fns in cb_info:
                notifications.register_event_callback(event, resource_type,
                                                      callback_fns)

    def revoke_by_user(self, user_id):
        return self.revoke(revoke_model.RevokeEvent(user_id=user_id))

    def _assert_not_domain_and_project_scoped(self, domain_id=None,
                                              project_id=None):
        if domain_id is not None and project_id is not None:
            msg = _('The revoke call must not have both domain_id and '
                    'project_id. This is a bug in the Keystone server. The '
                    'current request is aborted.')
            raise exception.UnexpectedError(exception=msg)

    def revoke_by_audit_id(self, audit_id):
        self.revoke(revoke_model.RevokeEvent(audit_id=audit_id))

    def revoke_by_audit_chain_id(self, audit_chain_id, project_id=None,
                                 domain_id=None):

        self.revoke(revoke_model.RevokeEvent(audit_chain_id=audit_chain_id,
                                             domain_id=domain_id,
                                             project_id=project_id))

    def check_token(self, token_values):
        """Check the values from a token against the revocation list.

        :param token_values: dictionary of values from a token, normalized for
                             differences between v2 and v3. The checked values
                             are a subset of the attributes of model.TokenEvent

        :raises keystone.exception.TokenNotFound: If the token is invalid.

        """
        if revoke_model.is_revoked(self.driver.list_events(), token_values):
            raise exception.TokenNotFound(_('Failed to validate token'))

    def revoke(self, event):
        self.driver.revoke(event)


@six.add_metaclass(abc.ABCMeta)
class RevokeDriverV8(object):
    """Interface for recording and reporting revocation events."""

    @abc.abstractmethod
    def list_events(self, last_fetch=None):
        """return the revocation events, as a list of objects.

        :param last_fetch:   Time of last fetch.  Return all events newer.
        :returns: A list of keystone.revoke.model.RevokeEvent
                  newer than `last_fetch.`
                  If no last_fetch is specified, returns all events
                  for tokens issued after the expiration cutoff.

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def revoke(self, event):
        """register a revocation event.

        :param event: An instance of
            keystone.revoke.model.RevocationEvent

        """
        raise exception.NotImplemented()  # pragma: no cover


Driver = manager.create_legacy_driver(RevokeDriverV8)
