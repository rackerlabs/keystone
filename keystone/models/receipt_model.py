# Copyright 2018 Catalyst Cloud Ltd
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

"""Unified in-memory receipt model."""

from oslo_utils import reflection
from oslo_utils import timeutils
import six


def _parse_and_normalize_time(time_data):
    if isinstance(time_data, six.string_types):
        time_data = timeutils.parse_isotime(time_data)
    return timeutils.normalize_time(time_data)


class KeystoneReceipt(dict):
    """An in-memory representation that unifies v3 receipts."""

    def __init__(self, receipt_id, receipt_data):
        self.receipt_data = receipt_data
        self.receipt_id = receipt_id
        super(KeystoneReceipt, self).__init__(**receipt_data['receipt'])

    def __repr__(self):
        """Return string representation of KeystoneReceipt."""
        desc = ('<%(type)s at %(loc)s>')
        self_cls_name = reflection.get_class_name(self, fully_qualified=False)
        return desc % {'type': self_cls_name, 'loc': hex(id(self))}

    @property
    def expires(self):
        return _parse_and_normalize_time(self['expires_at'])

    @property
    def issued(self):
        return _parse_and_normalize_time(self['issued_at'])

    @property
    def user_id(self):
        return self['user']['id']

    @property
    def user_name(self):
        return self['user']['name']

    @property
    def user_domain_id(self):
        return self['user']['domain']['id']

    @property
    def user_domain_name(self):
        return self['user']['domain']['name']

    @property
    def methods(self):
        return self.get('methods', [])
