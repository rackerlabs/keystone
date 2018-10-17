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

from keystone.common import provider_api
import keystone.conf


CONF = keystone.conf.CONF
PROVIDERS = provider_api.ProviderAPIs


def render_receipt_response_from_model(receipt):
    receipt_reference = {
        'receipt': {
            'methods': receipt.methods,
            'user': {
                'id': receipt.user['id'],
                'name': receipt.user['name'],
                'domain': {
                    'id': receipt.user_domain['id'],
                    'name': receipt.user_domain['name'],
                }
            },
            'expires_at': receipt.expires_at,
            'issued_at': receipt.issued_at,
        },
        'required_auth_methods': receipt.required_methods,
    }
    return receipt_reference
