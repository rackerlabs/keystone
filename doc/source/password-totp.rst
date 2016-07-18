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

Before disabling the V2 API you should configure your identity endpoint to be
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

Then restart Keystone, and confirm the API is inoperable.

Configuring MFA for your user account
=====================================

Before you can use MFA you will need to setup a TOTP credential, how to do that
is documented in:

:doc:`totp-credentials`

Once you have a TOTP credential associated with your user MFA is enabled and
you must provide a passcode when autheticating.

Authenticate with Password and TOTP
===================================

Once you have a valid application such as Google Authenticator setup with your
secret, it will provide you with a 6 digit passcode that is valid for 30 seconds.

Using your new TOTP credentials is done by simply appending your 6 digit passcode
to your standard password on any interactions with OpenStack APIs.

This applies for logging into Horizon, and can be done with the OpenStackClient
quite easily if it is not provided with a password as it will prompt for one.
