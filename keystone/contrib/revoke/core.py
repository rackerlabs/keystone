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

from flufl.enum import IntEnum

import abc
import six
import uuid

from keystone.common import dependency
from keystone.common import extension
from keystone.common import manager
from keystone import config
from keystone import exception
from keystone.openstack.common import log as logging

from oslo.config import cfg

CONF = config.CONF
LOG = logging.getLogger(__name__)

revoke_opts = [
    cfg.StrOpt('driver',
               default='keystone.contrib.revoke.backends.kvs.Revoke'),
]
CONF.register_group(cfg.OptGroup(name='revoke',
                                 title='Token Revocation List'))
CONF.register_opts(revoke_opts, group='revoke')


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
            'href': ('https://github.com/openstack/identity-api/ext/' +
                     'revoke.update-me-please'),
        }
    ]}
extension.register_v3_extension(EXTENSION_DATA['alias'], EXTENSION_DATA)


class ScopeType(IntEnum):
    domain = 1
    project = 2
    user = 3
    trust = 4


class RevokeEvent(object):
    def __init__(self, id, scope_id, scope_type, valid_until,
                 issued_at_or_after=None, issued_at_or_before=None,
                 expires_at_or_after=None, expires_at_or_before=None):
        for k, v in locals().copy().iteritems():
            setattr(self, k, v)

    @property
    def scope_type(self):
        return self._scope_type

    @scope_type.setter
    def scope_type(self, value):
        self._scope_type = ScopeType[value]


class EventIdentifier():
    def __init__(self, value=None):
        if value is None:
            self.value = uuid.uuid4()
        else:
            self.value = value


@dependency.provider('revoke_api')
class Manager(manager.Manager):
    """Example Manager.

    See :mod:`keystone.common.manager.Manager` for more details on
    how this dynamically calls the backend.

    """

    def __init__(self):
        super(Manager, self).__init__(CONF.revoke.driver)

    def revoke_by_expiration(self, user_id, expires_at):
        raise exception.NotImplemented()

    def revoke_by_user(self, user_id):
        event = RevokeEvent(EventIdentifier(), user_id, ScopeType.user)
        self.driver.revoke(event)

    def revoke_by_domain(self, domain_id):
        raise exception.NotImplemented()

    def revoke_by_project(self, project_id):
        raise exception.NotImplemented()

    def revoke_by_trust(self, trust_id):
        raise exception.NotImplemented()


@six.add_metaclass(abc.ABCMeta)
class Driver(object):
    """Interface description for Example driver."""

    @abc.abstractmethod
    def get_events(self, filter=None):
        """return the revocation events,

        :param filter:
        :raises: keystone.exception,
        :returns: Set of revocation events that match the filter.
                   If no filter is specified, returns all events
                   for tokens issued after the expiration cutoff.


        """
        raise exception.NotImplemented()

    @abc.abstractmethod
    def revoke(self, event):
        """return the revocation events,

        :param revocation:
        :raises: keystone.exception,
        :returns: The revocatione_event with an updated values

        """
        raise exception.NotImplemented()
