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

"""Keystone UID Token Provider"""

from __future__ import absolute_import

import string
import uuid

from keystone.token.providers import common


class Provider(common.BaseProvider):
    """Generates short URL-friendly tokens using UUID4 to provide entropy.

    Tokens will be either 21 or 22 characters in length.
    """
    ALPHABET = string.numbers + string.letters

    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)

    def _encode(cls, number):
        """Converts an integer to a string."""
        s = ''
        while number != 0:
            number, i = divmod(number, len(cls.ALPHABET))
            s = cls.ALPHABET[i] + s
        return s

    def _get_token_id(self, token_data):
        return Provider._encode(uuid.uuid4().int)
