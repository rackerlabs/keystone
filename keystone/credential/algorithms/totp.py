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

"""Time-based One-time Password Algorithm (TOTP) utilities

TOTP is an algorithm that computes a one-time password from a shared secret
key and the current time.

TOTP is an implementation of a hash-based message authentication code (HMAC).
It combines a secret key with the current timestamp using a cryptographic hash
function to generate a one-time password. The timestamp typically increases in
30-second intervals, so passwords generated close together in time from the
same secret key will be equal.
"""

import base64
import time
import uuid

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.twofactor import totp as crypto_totp
import six

from keystone import exception
from keystone.i18n import _


METHOD_NAME = 'totp'


def generate_passcode(secret):
    """Generate TOTP passcode.

    :param bytes secret: A base32 encoded secret for the TOTP authentication
    :returns: totp passcode as bytes
    """
    if isinstance(secret, six.text_type):
        # NOTE(dstanek): since this may be coming from the JSON stored in the
        # database it may be UTF-8 encoded
        secret = secret.encode('utf-8')

    decoded = base64.b32decode(secret)
    totp = crypto_totp.TOTP(
        decoded, 6, hashes.SHA1(), 30, backend=default_backend())
    return totp.generate(time.time())


def validate_secret(value):
    try:
        base64.b32decode(value)
    except TypeError:
        raise exception.ValidationError(
            message=_('Invalid base32 blob in credential'))


def generate_secret():
    """Returns a 128 base32 encoded secret for TOTP authentication."""
    return base64.b32encode(uuid.uuid4().bytes)
