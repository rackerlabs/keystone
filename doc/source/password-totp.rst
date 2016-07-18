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

======================================================================
Multi-Factor Auth via Password and Time-based One-time Password (TOTP)
======================================================================

Configuring Keystone for MFA
============================

The default password authentication plugin for Keystone now supports
Multi-Factor Auth (MFA) via a combination of TOTP and password for
authetication.

This feature is enabled once a credential of type 'totp' is associated
with your user.

While MFA is enabled by default, to be fully secure your deployment of Keystone
**must disable the V2 API** as it does not support MFA and regardless
of a user having a 'totp' credential will only require username and
password for authentication.

Disable V2 API
--------------

Before doing this you should configure your identity endpoint to be
versionless and setup all services to correctly use the V3 API.

To fully disable the V2 api in Keystone, in the 'keystone-paste.ini'
file find and comment out the lines as seen below.

/etc/keystone/keystone-paste.ini:: 

    [pipeline:public_api]
    # The last item in this pipeline must be public_service or an equivalent
    # application. It cannot be a filter.
    # pipeline = cors sizelimit http_proxy_to_wsgi osprofiler url_normalize
    request_id admin_token_auth build_auth_context token_auth json_body
    ec2_extension public_service

    [pipeline:admin_api]
    # The last item in this pipeline must be admin_service or an equivalent
    # application. It cannot be a filter.
    # pipeline = cors sizelimit http_proxy_to_wsgi osprofiler url_normalize
    request_id admin_token_auth build_auth_context token_auth json_body
    ec2_extension s3_extension admin_service

    ...

    [composite:main]
    use = egg:Paste#urlmap
    # /v2.0 = public_api
    /v3 = api_v3
    / = public_version_api

    [composite:admin]
    use = egg:Paste#urlmap
    # /v2.0 = admin_api
    /v3 = api_v3
    / = admin_version_api

Following that restart Keystone, and confirm the API is inoperable.

Configuring MFA for your user account
=====================================

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

Authenticate with Password and TOTP
===================================

Once you have a valid application such as Google Authenticator setup with your
secret, it will provide you with a 6 digit passcode that is valid for 30 seconds.

Using your new TOTP credentials is done by simply appending your 6 digit passcode
to your standard password on any interactions with OpenStack APIs.

This applies for logging into Horizon, and can be done with the OpenStackClient
quite easily if it is not provided with a password as it will prompt for one.
