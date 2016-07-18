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

========================================
Creating and setting up TOTP Credentials
========================================

Keystone has a couple of uses for the TOTP credential type, these
are further documented on their respective pages:

* :doc:`password-totp`
* :doc:`auth-totp`

But before you can use either of these you will need to create and setup some
TOTP credentials for your user.

How to setup your TOTP credentials
==================================

Create a TOTP secret
--------------------

TOTP uses a base32 encoded string for the secret. The secret must be at least
128 bits (16 bytes). The following python code can be used to generate a TOTP
secret:

.. code-block:: python

    import base64
    import os
    print base64.b32encode(os.urandom(20)).decode('utf-8')

Example output::

    ETOOAOQADYO6AKAUSFXH6ZSQQXGKFKBN

This randomly generated secret can then be used to add new 'totp' credentials
to a specific user.

Create an OpenStack TOTP credential
-----------------------------------

Once you have your secret, you must provide it to Keystone and associated it
with your user. The easiest way to do this is via the OpenStackClient.

.. code-block:: bash

    openstack --os-identity-api-version 3 \
        credential create <user_id> <secret> --type totp

One major limiting factor right now is that you must be admin to use the
credentials APIs, so if you are a non-admin user an admin will have to setup
your TOTP credential on your behalf.

Google Authenticator
--------------------

To make use of your secret, you need to be able to generate a 6 digit passcode.

On a device install Google Authenticator and inside the app click on 'Set up
account' and then click on 'Enter provided key'. In the input fields enter
account name and secret.  Optionally a QR code can be generated programatically
to avoid having to type the information.

Once done the app will provide you with a 6 digit passcode that is valid for
a 30 seconds.

QR code
-------

If you install the 'qrcode' python library:

.. code-block:: bash

    pip install qrcode

You can use the following code to create a TOTP QR code for your device:

.. code-block:: python

    import base64
    import os
    import qrcode

    secret = base64.b32encode(os.urandom(20)).decode('utf-8')

    uri = 'otpauth://totp/{name}?secret={secret}&issuer={issuer}'.format(
        name='name',
        secret=secret,
        issuer='Keystone')

    img = qrcode.make(uri)
    img.save('totp.png')

In Google Authenticator app click on 'Set up account' and then click on 'Scan
a barcode', and then scan the 'totp.png' image.  This should create a new TOTP
entry in the application.
