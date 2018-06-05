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

import os


from keystone.common import utils as ks_utils
import keystone.conf
from keystone.i18n import _
from keystone.receipt.providers import common
from keystone.receipt import receipt_formatters as tf


CONF = keystone.conf.CONF


class Provider(common.BaseProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)

        # NOTE(lbragstad): We add these checks here because if the fernet
        # provider is going to be used and either the `key_repository` is empty
        # or doesn't exist we should fail, hard. It doesn't make sense to start
        # keystone and just 500 because we can't do anything with an empty or
        # non-existant key repository.
        if not os.path.exists(CONF.fernet_receipts.key_repository):
            subs = {'key_repo': CONF.fernet_receipts.key_repository}
            raise SystemExit(_('%(key_repo)s does not exist') % subs)
        if not os.listdir(CONF.fernet_receipts.key_repository):
            subs = {'key_repo': CONF.fernet_receipts.key_repository}
            raise SystemExit(_('%(key_repo)s does not contain keys, use '
                               'keystone-manage fernet_setup to create '
                               'Fernet keys.') % subs)

        self.receipt_formatter = tf.ReceiptFormatter()

    def issue_receipt(self, *args, **kwargs):
        receipt_id, receipt_data = super(Provider, self).issue_receipt(
            *args, **kwargs)
        self._build_issued_at_info(receipt_id, receipt_data)
        return receipt_id, receipt_data

    def _build_issued_at_info(self, receipt_id, receipt_data):
        # NOTE(roxanaghe, lbragstad): We must use the creation time that
        # Fernet builds into it's receipt. The Fernet spec details that the
        # receipt creation time is built into the receipt, outside of the
        # payload provided by Keystone. This is the reason why we don't pass
        # the issued_at time in the payload. This also means that we shouldn't
        # return a receipt reference with a creation time that we created
        # when Fernet uses a different creation time. We should use the
        # creation time provided by Fernet because it's the creation time
        # that we have to rely on when we validate the receipt.
        fernet_creation_datetime_obj = self.receipt_formatter.creation_time(
            receipt_id)
        receipt_data['receipt']['issued_at'] = ks_utils.isotime(
            at=fernet_creation_datetime_obj, subsecond=True)

    def _get_receipt_id(self, receipt_data):
        """Generate the receipt_id based upon the data in receipt_data.

        :param receipt_data: receipt information
        :type receipt_data: dict
        :rtype: six.text_type

        """
        user_id = receipt_data['receipt']['user']['id']
        expires_at = receipt_data['receipt']['expires_at']
        methods = receipt_data['receipt'].get('methods')

        return self.receipt_formatter.create_receipt(
            user_id,
            expires_at,
            methods=methods
        )
