:orphan:

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

===============================
keystone federation and horizon
===============================

keystone changes
================

1. Update `trusted_dashboard` in keystone.conf.

Specify hostnames of trusted horizon servers. This value may be repeated
multiple times. This setting ensures that keystone only sends token data back
to trusted servers only. This is performed as a precaution, specifically to
prevent man-in-the-middle (MITM) attacks.

.. code-block:: ini

  [federation]
  trusted_dashboard = http://acme.horizon.com/auth/websso
  trusted_dashboard = http://beta.horizon.com/auth/websso

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

A remote id attribute indicates the header to retrieve from the WSGI
environment. This header should contain information about the identity
provider. For `mod_shib` this would be `Shib-Identity-Provider`, for
`mod_auth_openidc`, this could be `HTTP_OIDC_ISS`.

It is recommended that this option be set on a per-protocol basis.

.. code-block:: ini

  [saml2]
  remote_id_attribute = Shib-Identity-Provider
  [oidc]
  remote_id_attribute = HTTP_OIDC_ISS

Alternatively, a generic options may be set at the `[federation]` level.

.. code-block:: ini

  [federation]
  remote_id_attribute = HTTP_OIDC_ISS



4. Set `remote_ids` for a keystone identity provider.

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

horizon changes
===============

1. Set the Identity Service version to 3

Ensure the `OPENSTACK_API_VERSIONS` option in horizon's local_settings.py has
been updated to indicate that the `identity` version to use is `3`.

.. code-block:: ini

  OPENSTACK_API_VERSIONS = {
    "identity": 3,
  }

2. Authenticate against Identity Server v3.

Ensure the `OPENSTACK_KEYSTONE_URL` option in horizon's local_settings.py has
been updated to point to a v3 URL.

.. code-block:: ini

  OPENSTACK_KEYSTONE_URL = "http://localhost:5000/v3"

3. Enable the WebSSO setting.

Ensure the `WEBSSO_ENABLED` is set to True in horizon's local_settings.py file,
this will provide users with an updated login screen for horizon.

.. code-block:: ini

  WEBSSO_ENABLED = True

4. (Optional) Create a list of authentication methods with `WEBSSO_CHOICES`.

Within horizon's settings.py file, a list of supported authentication methods
can be specified. The entries in the list map to keystone federation protocols,
with the exception of `credentials` which is reserved by horizon, and maps to
the user name and password used by keystone's identity backend.

.. code-block:: ini

  WEBSSO_CHOICES = (
        ("credentials", _("Keystone Credentials")),
        ("oidc", _("OpenID Connect")),
        ("saml2", _("Security Assertion Markup Language"))
      )

5. (Optional) Specify an initial choice with `WEBSSO_INITIAL_CHOICE`.

The list set by `WEBSSO_CHOICES` will be generated in a drop-down menu in the
login screen. The setting `WEBSSO_INITIAL_CHOICE` will automatically set that
choice to be highlighted by default.

.. code-block:: ini

  WEBSSO_CHOICES = "credentials"
