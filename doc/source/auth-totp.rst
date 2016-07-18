..
      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

===================================
Time-based One-time Password (TOTP)
===================================

Configuring Keystone for TOTP Auth
==================================

TOTP is not enabled in Keystone by default.  To enable it add the ``totp``
authentication method to the ``[auth]`` section in ``keystone.conf``:

.. code-block:: ini

    [auth]
    methods = external,password,token,oauth1,totp

For a user to have access to TOTP, he must have configured TOTP credentials in
Keystone and a TOTP device for generating passcodes.

Configuring TOTP for your user
==============================

Before you can use TOTP Auth you will need to setup a TOTP credential, how to do
that is documented in:

:doc:`totp-credentials`

Authenticate with TOTP
======================

Google Authenticator will generate a 6 digit PIN (passcode) every few seconds.
Use the passcode and your user ID to authenticate using the ``totp`` method.

Tokens
------

Get a token with default scope (may be unscoped) using totp:

.. code-block:: bash

    USER_ID=b7793000f8d84c79af4e215e9da78654
    PASSCODE=012345

    curl -i \
      -H "Content-Type: application/json" \
      -d '
    { "auth": {
            "identity": {
                "methods": [
                    "totp"
                ],
                "totp": {
                    "user": {
                        "id": "'$USER_ID'",
                        "passcode": "'$PASSCODE'"
                    }
                }
            }
        }
    }' \
      http://localhost:5000/v3/auth/tokens ; echo
