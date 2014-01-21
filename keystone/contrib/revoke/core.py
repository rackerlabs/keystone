# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack Foundation
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


import abc
import six

from keystone.common import dependency
from keystone.common import extension
from keystone.common import manager
from keystone import config
from keystone.contrib.revoke import model
from keystone import exception
from keystone.openstack.common import log

CONF = config.CONF
LOG = log.getLogger(__name__)


EXTENSION_DATA = {
    'name': 'OpenStack REVOKE API',
    'namespace': 'http://docs.openstack.org/identity/api/ext/'
                 'OS-REVOKE/v1.0',
    'alias': 'OS-REVOKE',
    'updated': '2013-07-07T12:00:0-00:00',
    'description': 'OpenStack Revoked Token Reporting mechanism.',
    'links': [
        {
            'rel': 'describedby',
            'type': 'text/html',
            'href': ('https://github.com/openstack/identity-api/blob/master/' +
                     'openstack-identity-api/v3/src/markdown/' +
                     'identity-api-v3-os-revoke-ext.md'),
        }, {
            'rel': 'LIST',
            'type': 'application/JSON',
            'href': ('OS-REVOKE/events'),
        }
    ]}
extension.register_v3_extension(EXTENSION_DATA['alias'], EXTENSION_DATA)


@dependency.provider('revoke_api')
class Manager(manager.Manager):
    """Revoke API Manager.

    Performs common logic for recording revocations.

    """

    def __init__(self):
        super(Manager, self).__init__(CONF.revoke.driver)

    def revoke_by_expiration(self, user_id, expires_at):
        event = model.RevokeEvent(id=model.EventIdentifier(),
                                  user_id=user_id,
                                  expires_at=expires_at)
        self.driver.revoke(event)

    def revoke_by_user(self, user_id):
        event = model.RevokeEvent(id=model.EventIdentifier(),
                                  user_id=user_id)
        self.driver.revoke(event)

    def revoke_by_domain(self, domain_id):
        event = model.RevokeEvent(id=model.EventIdentifier(),
                                  domain_id=domain_id)
        self.driver.revoke(event)

    def revoke_by_user_and_project(self, user_id, project_id):
        event = model.RevokeEvent(id=model.EventIdentifier(),
                                  project_id=project_id,
                                  user_id=user_id)
        self.driver.revoke(event)

    #TODO(ayoung): this needs a unit test
    def revoke_by_user_and_domain(self, user_id, domain_id):
        event = model.RevokeEvent(id=model.EventIdentifier(),
                                  domain_id=domain_id,
                                  user_id=user_id)
        self.driver.revoke(event)

    def revoke_by_project(self, project_id):
        event = model.RevokeEvent(id=model.EventIdentifier(),
                                  project_id=project_id)
        self.driver.revoke(event)

    #TODO(ayoung): this needs a unit test
    def revoke_by_trust(self, trust_id):
        event = model.RevokeEvent(id=model.EventIdentifier(),
                                  trust_id=trust_id)
        self.driver.revoke(event)

    def revoke_by_project_role_assignment(self, project_id, role_id):
        event = model.RevokeEvent(id=model.EventIdentifier(),
                                  project_id=project_id,
                                  role_id=role_id)
        self.driver.revoke(event)

    def revoke_by_domain_role_assignment(self, domain_id, role_id):
        event = model.RevokeEvent(id=model.EventIdentifier(),
                                  domain_id=domain_id,
                                  role_id=role_id)
        self.driver.revoke(event)

    #TODO(ayoung): this needs a unit test
    def revoke_for_consumer(self, consumer_id):
        event = model.RevokeEvent(id=model.EventIdentifier(),
                                  consumer_id=consumer_id)
        self.driver.revoke(event)

    def check_token(self, token_values):
        """ check values from a token against the revocation list

        :param  dictionary of values from a token, 
        normalized for differences between v2 and v3. The checked values are a
         subset of the attributes of model.TokenEvent
        :raises exception.TokenNotFound if the token is invalid
        :returns no value returned
         """ 
        
        def revoke_matches(event, token_values):
            #something has to match in order to revoke the token
            matched = False
            if event.user_id is not None:
                if event.user_id != token_values['user_id']:
                    return False
                else:
                    matched = True

            if event.project_id is not None:
                if event.project_id != token_values['project_id']:
                    return False
                else:
                    matched = True

            if event.domain_id is not None:
                if event.domain_id != token_values['domain_id']:
                    return False
                else:
                    matched = True

            if event.expires_at is not None:
                token_date = token_values['expires_at']
                if event.expires_at != token_date:
                    return False
                else:
                    matched = True

            if event.trust_id is not None:
                if event.trust_id != token_values['trust_id']:
                    return False
                else:
                    matched = True

            if event.consumer_id is not None:
                if event.consumer_id != token_values['consumer_id']:
                    return False
                else:
                    matched = True
            return matched

        events = self.get_events(filter=None)
        for event in events:
            if revoke_matches(event, token_values):
                raise exception.TokenNotFound(_('Failed to validate token'))


@six.add_metaclass(abc.ABCMeta)
class Driver(object):
    """Interface for recording and reporting revocation Events."""

    @abc.abstractmethod
    def get_events(self, filter=None):
        """return the revocation events, as a list of  objects

        :param filter:   Not yet supported.
        :raises: keystone.exception,
        :returns: A list of keystone.contrib.revoke.model.RevokeEvent 
                  that match the filter.
                  If no filter is specified, returns all events
                  for tokens issued after the expiration cutoff.


        """
        raise exception.NotImplemented()

    @abc.abstractmethod
    def revoke(self, event):
        """register a revocation event

        :param event: An instance of keystone.contrib.revoke.model.RevocationEvent

        """
        raise exception.NotImplemented()
