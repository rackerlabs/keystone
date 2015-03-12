:orphan:

..
      Copyright 2011-2013 OpenStack, Foundation
      All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

      http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

===============================
Keystone Federation and Horizon
===============================

1. Update `trusted_dashboard` in keystone.conf.

Specify hostnames of trusted horizon servers. This value may be repeated
multiple times. This setting ensures that keystone only sends token data back
to trusted servers only. This is performed as a precaution, specifically to
prevent man-in-the-middle (MITM) attacks.

.. code-block:: ini

  [federation]
  trusted_dashboard = http://acme.horizon.com
  trusted_dashboard = http://beta.horizon.com

2. Update Apache vhost file with websso information.

The route `/v3/auth/OS-FEDERATION/websso/` must be protected by the chosen
Apache module. This is performed so the request that originates from horizon
will use the same identity provider that keystone configured. Below is an
example if `mod_auth_openidc` is selected. If `mod_shib` was used, then
`AuthType` would be `shibboleth`.

.. code-block:: xml

  <VirtualHost *:5000>

      ...

      <LocationMatch /v3/auth/OS-FEDERATION/websso/.*>
        AuthType openid-connect
        Require valid-user
      </LocationMatch>
  </VirtualHost>

3. Update `remote_id_attribute` in keystone.conf.

A remote id attribute indicated the the header to retrieve from the WSGI
environment. This header should contain information about the identity
provider. For `mod_shib` this would be `Shib-Identity-Provider`, for
`mod_auth_openidc`, this could be `HTTP_OIDC_ISS`.

.. code-block:: ini

  [federation]
  remote_id_attribute = HTTP_OIDC_ISS

4. Set `remote_id` for a keystone identity provider.

A keystone identity provider may have multiple `remote_ids` specified, this
setting allows the same *keystone* identity provider resource to be used
with multiple external identity providers. For example, an identity
provider resource may be called `university-idp`, and it's `remote_ids`
could be ['university-x', 'university-y', 'university-z']. Removing the
need to configure N identity provider resources in keystone.

.. NOTE::

    It's important to know that in the case of using horizon and keystone
    federation, it is necessary to set the keystone IdP entry ID to the
    value that will be returned from the `remote_id_attribute` key.

    For instance, if `remote_id_attribute` is set as `HTTP_OIDC_ISS`,
    a typical value would be `accounts.example.com`. This should be the
    ID for the Identity Providers in keystone.

    The motivation for this approach was to have ensure there is some
    identity provider data in an assertion. Thus removing the requirement for
    horizon to list multiple (or all) identity providers from keystone.
