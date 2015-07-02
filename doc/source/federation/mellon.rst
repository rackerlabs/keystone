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

============
Setup Mellon
============

Configure Apache HTTPD for mod_auth_mellon
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Follow the steps outlined at: `Running Keystone in HTTPD`_.

.. _`Running Keystone in HTTPD`: ../apache-httpd.html

You'll also need to install the Apache module `mod_auth_mellon
<https://github.com/UNINETT/mod_auth_mellon>`_.  For example:

.. code-block:: bash

    $ apt-get install libapache2-mod-auth-mellon

Configure your Keystone virtual host and adjust the config to properly handle SAML2 workflow:

Add *WSGIScriptAlias* directive to your vhost configuration::

    WSGIScriptAliasMatch ^(/v3/OS-FEDERATION/identity_providers/.*?/protocols/.*?/auth)$ /var/www/keystone/main/$1

Make sure the *wsgi-keystone.conf* contains a *<Location>* directive for the Mellon module and
a *<Location>* directive for each identity provider::

    <Location /v3>
        MellonEnable "info"
        MellonSPPrivateKeyFile /etc/httpd/mellon/http_keystone.fqdn_keystone.key
        MellonSPCertFile /etc/httpd/mellon/http_keystone.fqdn_keystone.cert
        MellonSPMetadataFile /etc/httpd/mellon/http_keystone.fqdn_keystone.xml
        MellonIdPMetadataFile /etc/httpd/mellon/idp-metadata.xml
        MellonEndpointPath /v3/OS-FEDERATION/identity_providers/idp_1/protocols/saml2/auth/mellon
        MellonIdP "IDP"
    </Location>

    <Location /v3/OS-FEDERATION/identity_providers/idp_1/protocols/saml2/auth>
        AuthType "Mellon"
        MellonEnable "auth"
    </Location>

.. NOTE::
    * See below for information about how to generate the values for the
      `MellonSPMetadataFile`, etc. directives.
    * ``saml2`` may be different in your deployment, but do not use a wildcard value.
      Otherwise *every* federated protocol will be handled by Mellon.
    * ``idp_1`` has to be replaced with the name associated with the IdP in Keystone.
    * You are advised to carefully examine `mod_auth_mellon Apache
      configuration documentation
      <https://github.com/UNINETT/mod_auth_mellon>`_

Enable the Keystone virtual host, for example:

.. code-block:: bash

    $ a2ensite wsgi-keystone.conf

Enable the ``ssl`` and ``auth_mellon`` modules, for example:

.. code-block:: bash

    $ a2enmod ssl
    $ a2enmod auth_mellon

Restart Apache, for example:

.. code-block:: bash

    $ service apache2 restart

Configuring the Mellon SP Metadata
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Mellon provides a script called ``mellon_create_metadata.sh`` which generates the
values for the config directives `MellonSPPrivateKeyFile`, `MellonSPCertFile`,
and `MellonSPMetadataFile`.  It is run like this:

.. code-block:: bash

    $ mellon_create_metadata.sh http://keystone.fqdn:5000/keystone \
      http://keystone.fqdn:5000/v3/OS-FEDERATION/identity_providers/idp_1/protocols/saml2/auth/mellon

The first parameter is used as the entity ID, a unique identifier for this
Keystone SP.  You do not have to use the URL, but it is an easy way to uniquely
identify each Keystone SP.  The second parameter is the full URL for the
endpoint path corresponding to the parameter `MellonEndpointPath`.

Fetch your Service Provider's Metadata file.  This corresponds to the value of
the `MellonIdPMetadataFile` directive above. For example:

.. code-block:: bash

    $ wget --cacert /path/to/ca.crt -O /etc/httpd/mellon/idp-metadata.xml \
      https://idp.fqdn/idp/saml2/metadata

Upload your Service Provider's Metadata file to your Identity Provider.  For
example:

.. code-block:: bash

    $ echo -n "idp_username" > /etc/httpd/mellon/idp_username.txt
    $ echo -n "idp_password" > /etc/httpd/mellon/idp_password.txt
    $ curl --cacert /path/to/ca.crt \
         --data-urlencode login_name@/etc/httpd/mellon/idp_username.txt \
         --data-urlencode login_password@/etc/httpd/mellon/idp_password.txt \
         -b /etc/httpd/mellon/cookies -c /etc/httpd/mellon/cookies \
         https://idp.fqdn/idp/login/form
    $ curl --cacert /path/to/ca.crt \
         --referer https://idp.fqdn/idp/rest/providers/saml2/SPS/keystone \
         -b /etc/httpd/mellon/cookies -c /etc/httpd/mellon/cookies \
         --data-urlencode metadata@/etc/httpd/mellon/http_keystone.fqdn_keystone.xml \
         https://idp.fqdn/idp/rest/providers/saml2/SPS/keystone
    $ rm -f /etc/httpd/mellon/idp_username.txt /etc/httpd/mellon/idp_password.txt /etc/httpd/mellon/cookies

Once you are done, restart Apache:

.. code-block:: bash

    $ service apache2 restart
