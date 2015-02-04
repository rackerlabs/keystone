..
    Licensed under the Apache License, Version 2.0 (the "License"); you may not
    use this file except in compliance with the License. You may obtain a copy
    of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
    License for the specific language governing permissions and limitations
    under the License.

================================================
Configuring Keystone for Tokenless Authorization
================================================

-----------
Definitions
-----------
* `X.509 Tokenless Authorization`: Provides a means to authorize client
    operations within Keystone by using an X.509 SSL client certificate
    without having to issue a token.

Prerequisites
-------------
Keystone must be running in a web container with https enabled; tests have
been done with Apache. Please refer to `running-keystone-in-httpd`_ and
`apache-certificate-and-key-installation`_ as references for this setup.

.. _`running-keystone-in-httpd`: http://docs.openstack.org/developer/keystone/apache-httpd.html
.. _`apache-certificate-and-key-installation`: https://www.digitalocean.com/community/tutorials/how-to-create-a-ssl-certificate-on-apache-for-ubuntu-14-04

--------------------
Apache Configuration
--------------------

Make sure to enable SSL and have client authentication (``SSLVerifyClient``)
set as ``optional`` to allow other token authentication methods. And attribute
``SSLOptions`` needs to set as ``+StdEnvVars`` to allow certificate attributes
to be passed. For example:

.. code-block:: ini

    SSLEngine on
    SSLCertificateFile    /etc/apache2/ssl/apache.crt
    SSLCertificateKeyFile /etc/apache2/ssl/apache.key
    SSLCACertificatePath /etc/apache2/cacertpath
    SSLOptions +StdEnvVars
    SSLVerifyClient optional

----------------------
Keystone Configuration
----------------------
The following configurable options can be defined in `keystone.conf`:

* ``trusted_issuer`` - The list of trusted issuers to further filter the
  certificates that are allowed to participate in the X.509 tokenless
  authorization. If the option is absent then no certificates will be
  allowed. The naming format for the attributes of a Distinguished Name(DN)
  must be separated by a comma and contain no spaces. This configuration
  option may be repeated for multiple values. For example::
  trusted_issuer=CN=john,OU=keystone,O=openstack
  trusted_issuer=CN=mary,OU=eng,O=abc
* ``protocol`` - The protocol name for the X.509 tokenless authorization
  along with the IdP name to look up its corresponding mapping. It defaults
  to ``x509``.
* ``issuer_attribute`` - The issuer attribute that is served as an IdP for
  the X.509 tokenless authorization along with the protocol to look up its
  corresponding mapping. It is the attribute name in the WSGI enviornment
  that references to the Issuer of the client certificate. It defaults to
  ``SSL_CLIENT_I_DN``.
* ``ephemeral_user`` - If this option is ``True``, the user referenced from
  the client certificate CN does not need to exist. A group needs to be
  defined in the corresponding mapping and this ephemeral user will have the
  same roles as what are assigned to the group. It defaults to ``False``.

This is a sample configuration for two `trusted_issuer`, a `protocol` set to
``ephemeral``, and `ephemeral_user` set to ``True``.

.. code-block:: ini

    [tokenless_auth]
    trusted_issuer = emailAddress=mary@abc.com,CN=mary,OU=eng,O=abc,L=San Jose,ST=California,C=US
    trusted_issuer = emailAddress=john@openstack.com,CN=john,OU=keystone,O=openstack,L=Sunnyvale,ST=California,C=US
    protocol = ephemeral
    ephemeral_user = True

-------------
Setup Mapping
-------------
Like federation, X.509 tokenless authorization also utilizes the mapping
mechanism to formulate an identity. The identity provider must correspond
to the issuer of the X.509 SSL client certificate. The protocol for the
given identity is ``x509`` by default, but can be configurable.

Create an IdP
-------------

The name of the IdP will need to be created from the client issuer DN. The
following sample is how a generic issuer DN looks like in a certificate.

.. code-block:: ini

    E=john@openstack.com
    CN=john
    OU=keystone
    O=openstack
    L=Sunnyvale
    S=California
    C=US

It should contain no spaces and have the right order seperated by commas
like the example below. Please be aware that ``emailAddress`` and ``ST``
should be used instead of ``E`` and ``S`` that are shown in the above
example. The following is the sample Python code used to create the IdP
name.

.. code-block:: python

    issuer_dn = 'emailAddress=john@openstack.com,CN=john,OU=keystone,
        O=openstack,L=Sunnyvale,ST=California,C=US'
    hashed_idp = hashlib.sha256(issuer_dn)
    idp_name = hashed_idp.hexdigest()

Create a Map
------------

By default, ``ephemeral_user`` is set to ``False``. In this case, the
mapping must yield a valid local user. When the client certificate has
``Subject DN`` as ``CN=alex,OU=eng,O=nice-network,L=Sunnyvale,
ST=California,C=US``, in the following examples, ``user_name`` will be
mapped to``alex`` and ``domain_name`` will be mapped to ``nice-network``.

Please refer to `mod_ssl`_ for the detailed mapping attributes.

.. _`mod_ssl`: http://httpd.apache.org/docs/current/mod/mod_ssl.html

.. code-block:: javascript

    {
         "mapping": {
             "rules": [
                 {
                     "local": [
                         {
                            "user": {
                                "user_name": "{0}",
                                "domain_name": "{1}"
                            }
                         }
                    ],
                    "remote": [
                        {
                            "type": "SSL_CLIENT_S_DN_CN"
                        },
                        {
                            "type": "SSL_CLIENT_S_DN_O"
                        }
                    ]
                }
            ]
        }
    }

However, if ``ephemeral_user`` is set to ``True``, the mapping must yield at
least one valid local group. For example:

.. code-block:: javascript

    {
         "mapping": {
             "rules": [
                 {
                     "local": [
                         {
                            "user": {
                                "user_name": "{0}"
                            }
                         },
                         {
                            "group": {
                                "id": "12345678"
                            }
                         }
                    ],
                    "remote": [
                        {
                            "type": "SSL_CLIENT_S_DN_CN"
                        }
                    ]
                }
            ]
        }
    }

Create a Protocol
-----------------

The name of the protocol will be the one defined in `keystone.conf` as
protocol which defaults to ``x509``.

A protocol name and an IdP name will uniquely identify a mapping.

-------------------------------
Setup ``auth_token`` middleware
-------------------------------

Configurable Options
--------------------
The following configurable options in ``auth_token`` middleware
should set to the correct values:

* ``auth_protocol`` - Set to ``https``.
* ``certfile`` - Set to the full path of the certificate file.
* ``keyfile`` - Set to the full path of the private key file.
* ``cafile`` - Set to the full path of the trusted CA certificate file.

Scope Information
-----------------
The scope information will be passed from the headers with the following
keywords to:

* ``X-Project-Id`` - If specified, its the project scope.
* ``X-Project-Name`` - If specified, its the project scope.
* ``X-Project-Domain-Id`` - If specified, its the domain of project scope.
* ``X-Project-Domain-Name`` - If specified, its the domain of project scope.
* ``X-Domain-Id`` - If specified, its the domain scope.
* ``X-Domain-Name`` - If specified, its the domain scope.
