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

import time
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.hashes import SHA1
from cryptography.hazmat.primitives.twofactor.totp import TOTP


"""Time-based One-time Password Algorithm (TOTP) is an algorithm that computes
a one-time password from a shared secret key and the current time.

TOTP is an implementation of a hash-based message authentication code (HMAC).
It combines a secret key with the current timestamp using a cryptographic hash
function to generate a one-time password. The timestamp typically increases in
30-second intervals, so passwords generated close together in time from the
same secret key will be equal.
"""


def get_totp_token(secret):
    """Generate HOTP code.

    :param secret: A secret for the TOTP authentication
    :returns: totp passcode
    """
    totp = TOTP(str(secret), 6, SHA1(), 30, backend=default_backend())
    return totp.generate(time.time())
