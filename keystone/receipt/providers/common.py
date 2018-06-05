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

from __future__ import absolute_import

import base64
import datetime
import uuid

from oslo_log import log
from oslo_utils import timeutils
import six

from keystone.common import provider_api
from keystone.common import utils
import keystone.conf
from keystone import exception
from keystone.i18n import _
from keystone.models import receipt_model
from keystone.receipt.providers import base


LOG = log.getLogger(__name__)
CONF = keystone.conf.CONF
PROVIDERS = provider_api.ProviderAPIs


def default_expire_time():
    """Determine when a fresh receipt should expire.

    Expiration time varies based on configuration (see
    ``[receipt] expiration``).

    :returns: a naive UTC datetime.datetime object

    """
    expire_delta = datetime.timedelta(seconds=CONF.receipt.expiration)
    expires_at = timeutils.utcnow() + expire_delta
    return expires_at.replace(microsecond=0)


def random_urlsafe_str():
    """Generate a random URL-safe string.

    :rtype: six.text_type

    """
    # chop the padding (==) off the end of the encoding to save space
    return base64.urlsafe_b64encode(uuid.uuid4().bytes)[:-2].decode('utf-8')


class V3ReceiptDataHelper(provider_api.ProviderAPIMixin, object):
    """Receipt data helper."""

    def __init__(self):
        # Keep __init__ around to ensure dependency injection works.
        super(V3ReceiptDataHelper, self).__init__()

    def _get_filtered_domain(self, domain_id):
        """Ensure the domain is enabled and return domain id and name.

        :param domain_id: The ID of the domain to validate
        :returns: A dictionary containing two keys, the `id` of the domain and
                  the `name` of the domain.
        """
        domain_ref = PROVIDERS.resource_api.get_domain(domain_id)
        if not domain_ref.get('enabled'):
            msg = _('Unable to validate receipt because domain %(id)s is '
                    'disabled') % {'id': domain_ref['id']}
            LOG.warning(msg)
            raise exception.DomainNotFound(msg)
        return {'id': domain_ref['id'], 'name': domain_ref['name']}

    def _populate_user(self, receipt_data, user_id):
        if 'user' in receipt_data:
            # no need to repopulate user if it already exists
            return

        user_ref = PROVIDERS.identity_api.get_user(user_id)
        filtered_user = {
            'id': user_ref['id'],
            'name': user_ref['name'],
            'domain': self._get_filtered_domain(user_ref['domain_id'])}
        receipt_data['user'] = filtered_user

    def _populate_receipt_dates(self, receipt_data, expires=None,
                                issued_at=None):
        if not expires:
            expires = default_expire_time()
        if not isinstance(expires, six.string_types):
            expires = utils.isotime(expires, subsecond=True)
        receipt_data['expires_at'] = expires
        receipt_data['issued_at'] = (issued_at or
                                     utils.isotime(subsecond=True))

    def get_receipt_data(self, user_id, method_names, expires=None,
                         receipt=None, issued_at=None):
        receipt_data = {'methods': method_names}

        # We've probably already written these to the receipt
        if receipt and 'user' in receipt:
            receipt_data['user'] = receipt['user']

        self._populate_user(receipt_data, user_id)
        self._populate_receipt_dates(receipt_data, expires=expires,
                                     issued_at=issued_at)
        return {'receipt': receipt_data}


class BaseProvider(provider_api.ProviderAPIMixin, base.Provider):
    def __init__(self, *args, **kwargs):
        super(BaseProvider, self).__init__(*args, **kwargs)
        self.v3_receipt_data_helper = V3ReceiptDataHelper()

    def get_receipt_version(self, receipt_data):
        if receipt_data and isinstance(receipt_data, dict):
            if 'receipt_version' in receipt_data:
                if receipt_data['receipt_version'] in receipt_model.VERSIONS:
                    return receipt_data['receipt_version']
        raise exception.UnsupportedReceiptVersionException()

    def issue_receipt(self, user_id, method_names, expires_at=None):
        receipt_data = self.v3_receipt_data_helper.get_receipt_data(
            user_id,
            method_names,
            expires=expires_at)

        receipt_id = self._get_receipt_id(receipt_data)
        return receipt_id, receipt_data

    def validate_receipt(self, receipt_id):
        try:
            (user_id, methods, issued_at, expires_at) = \
                self.receipt_formatter.validate_receipt(receipt_id)
        except exception.ValidationError as e:
            raise exception.ReceiptNotFound(e)

        return self.v3_receipt_data_helper.get_receipt_data(
            user_id,
            method_names=methods,
            issued_at=issued_at,
            expires=expires_at)
