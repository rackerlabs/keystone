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

"""Receipt provider interface."""

import datetime

from oslo_log import log
from oslo_utils import timeutils

from keystone.common import cache
from keystone.common import manager
from keystone.common import provider_api
import keystone.conf
from keystone import exception
from keystone.i18n import _
from keystone.models import receipt_model
from keystone import notifications


CONF = keystone.conf.CONF
LOG = log.getLogger(__name__)
PROVIDERS = provider_api.ProviderAPIs

RECEIPTS_REGION = cache.create_region(name='receipts')
MEMOIZE_RECEIPTS = cache.get_memoization_decorator(
    group='receipt',
    region=RECEIPTS_REGION)


# supported receipt versions
V3 = receipt_model.V3
VERSIONS = receipt_model.VERSIONS


class Manager(manager.Manager):
    """Default pivot point for the receipt provider backend.

    See :mod:`keystone.common.manager.Manager` for more details on how this
    dynamically calls the backend.

    """

    driver_namespace = 'keystone.receipt.provider'
    _provides_api = 'receipt_provider_api'

    V3 = V3
    VERSIONS = VERSIONS

    def __init__(self):
        super(Manager, self).__init__(CONF.receipt.provider)
        self._register_callback_listeners()

    def _register_callback_listeners(self):
        # This is used by the @dependency.provider decorator to register the
        # provider (receipt_provider_api) manager to listen for trust deletions
        callbacks = {
            notifications.ACTIONS.internal: [
                [notifications.INVALIDATE_RECEIPT_CACHE,
                    self._drop_receipt_cache],
            ]
        }

        for event, cb_info in callbacks.items():
            for resource_type, callback_fns in cb_info:
                notifications.register_event_callback(event, resource_type,
                                                      callback_fns)

    def _drop_receipt_cache(self, service, resource_type, operation, payload):
        """Invalidate the entire receipt cache.

        This is a handy private utility method that should be used when
        consuming notifications that signal invalidating the receipt cache.

        """
        if CONF.receipt.cache_on_issue:
            RECEIPTS_REGION.invalidate()

    def validate_receipt(self, receipt_id, window_seconds=0):
        if not receipt_id:
            raise exception.ReceiptNotFound(_('No receipt in the request'))

        try:
            receipt_ref = self._validate_receipt(receipt_id)
            self._is_valid_receipt(receipt_ref, window_seconds=window_seconds)
            return receipt_ref
        except exception.Unauthorized as e:
            LOG.debug('Unable to validate receipt: %s', e)
            raise exception.ReceiptNotFound(receipt_id=receipt_id)

    @MEMOIZE_RECEIPTS
    def _validate_receipt(self, receipt_id):
        return self.driver.validate_receipt(receipt_id)

    def _is_valid_receipt(self, receipt, window_seconds=0):
        """Verify the receipt is valid format and has not expired."""
        current_time = timeutils.normalize_time(timeutils.utcnow())

        try:
            receipt_data = receipt.get('receipt', receipt.get('access'))
            expires_at = receipt_data.get('expires_at',
                                          receipt_data.get('expires'))

            expiry = timeutils.parse_isotime(expires_at)
            expiry = timeutils.normalize_time(expiry)

            # add a window in which you can fetch a receipt beyond expiry
            expiry += datetime.timedelta(seconds=window_seconds)

        except Exception:
            LOG.exception('Unexpected error or malformed receipt '
                          'determining receipt expiry: %s', receipt)
            raise exception.ReceiptNotFound(_('Failed to validate receipt'))

        if current_time < expiry:
            return None
        else:
            raise exception.ReceiptNotFound(_('Failed to validate receipt'))

    def issue_receipt(self, user_id, method_names, expires_at=None,
                      auth_context=None):
        receipt_id, receipt_data = self.driver.issue_receipt(
            user_id, method_names, expires_at=expires_at,
            auth_context=auth_context)

        if CONF.receipt.cache_on_issue:
            self._validate_receipt.set(
                receipt_data, RECEIPTS_REGION, receipt_id)

        return receipt_id, receipt_data
