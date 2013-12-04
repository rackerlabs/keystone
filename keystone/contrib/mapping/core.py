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

"""Extension supporting Mapping for Clouds Federation."""

import abc
import six

from keystone.common import dependency
from keystone.common import extension
from keystone.common import manager
from keystone import config
from keystone import exception
from keystone.openstack.common import log as logging

CONF = config.CONF
LOG = logging.getLogger(__name__)
EXTENSION_DATA = {
    'name': 'OpenStack Mapping API',
    'namespace': 'http://docs.openstack.org/identity/api/ext/'
                 'OS-MAP/v1.0',
    'alias': 'OS-MAP',
    'updated': '2013-07-07T12:00:0-00:00',
    'description': 'OpenStack Mapping Mechanism.',
    'links': [
        {
            'rel': 'describedby',
            'type': 'text/html',
            'href': 'https://github.com/openstack/identity-api',
        }
    ]}
extension.register_admin_extension(EXTENSION_DATA['alias'], EXTENSION_DATA)
extension.register_public_extension(EXTENSION_DATA['alias'], EXTENSION_DATA)


def validate_mapping_structure(ref):
    name = ref.get('name')
    _check_name(name)

    rules = ref.get('rules')
    _check_rule_structure(rules)

    for rule in rules:
        local = rule.get('local')
        _check_local_structure(local)

        remote_list = rule.get('remote')
        _check_remote_list(remote_list)

        for remote in remote_list:
            _check_remote_entity(remote)


def _check_name(name):
    if not name or not (isinstance(name, str)
                        or isinstance(name, unicode)):
        msg = _("mapping object requires a name")
        raise exception.ValidationError(msg)


def _check_rule_structure(rules):
    if not rules or not isinstance(rules, list):
        msg = _("mapping object requires a list of rules")
        raise exception.ValidationError(msg)
    if len(rules) < 1:
        msg = _("mapping object requires at least 1 rule")
        raise exception.ValidationError(msg)


def _check_local_structure(local):
    if not local:
        msg = _("rule must have a local attribute")
        raise exception.ValidationError(msg)

    local_keys = local.keys()
    for key in local_keys:
        if key not in ['user.id', 'user.name', 'group', 'domain']:
            msg = _("local key must be either: user.id,"
                    "user.name, group or domain")
            raise exception.ValidationError(msg)


def _check_remote_list(remote_list):
    if not remote_list and not isinstance(remote_list, list):
        msg = _("rules require a list of remote attributes")
        raise exception.ValidationError(msg)
    if len(remote_list) < 1:
        msg = _("rules require at least 1 remote attribute")
        raise exception.ValidationError(msg)


def _check_remote_entity(remote_entity):
    remote_type = remote_entity.get('type')
    if not remote_type and not isinstance(remote_type, str):
        msg = _("remote attribute requires a type with value string")
        raise exception.ValidationError(msg)

    requirement = remote_entity.get('requirement')
    if not requirement and not isinstance(requirement, str):
        msg = _("remote attribute requires a requirement value")
        raise exception.ValidationError(msg)
    if requirement not in ['any_one_of', 'any_value_of', 'not_any_of']:
        msg = _("requirement must be either: any_one_of"
                "any_value_of, or not_any_of")
        raise exception.ValidationError(msg)

    values = remote_entity.get('values')
    if not values and not isinstance(values, list):
        msg = _("remote attribute require a list of values")
        raise exception.ValidationError(msg)


@dependency.provider('mapping_api')
class Manager(manager.Manager):
    """Default pivot point for the Mapping backend.

    See :mod:`keystone.common.manager.Manager` for more details on how this
    dynamically calls the backend.

    """
    def __init__(self):
        super(Manager, self).__init__(CONF.mapping.driver)


@six.add_metaclass(abc.ABCMeta)
class Driver(object):
    """Interface description for a Mapping driver."""

    @abc.abstractmethod
    def create_mapping(self, mapping_ref):
        """Create a mapping.

        :param mapping_ref: mapping ref with mapping name
        :type mapping_ref: dict
        :returns: mapping_ref

        """
        raise exception.NotImplemented()

    @abc.abstractmethod
    def update_mapping(self, mapping_id, mapping_ref):
        """Update a mapping.

        :param mapping_id: id of mapping to update
        :type mapping_id: string
        :param mapping_ref: new mapping ref
        :type mapping_ref: dict
        :returns: mapping_ref

        """
        raise exception.NotImplemented()

    @abc.abstractmethod
    def list_mappings(self):
        """List all mappings.

        returns: list of mappings

        """
        raise exception.NotImplemented()

    @abc.abstractmethod
    def get_mapping(self, mapping_id):
        """Get a mapping, returns the mapping based
        on mapping_id.

        :param mapping_id: id of mapping to get
        :type mapping_ref: string
        :returns: mapping_ref

        """
        raise exception.NotImplemented()

    @abc.abstractmethod
    def delete_mapping(self, mapping_id):
        """Delete a mapping.

        :param mapping_id: id of mapping to delete
        :type mapping_ref: string
        :returns: None

        """
        raise exception.NotImplemented()
