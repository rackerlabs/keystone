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
* ``X.509 Tokenless Authorization``
    Provides a means to authorize client operations with in Keystone by
    using a X.509 SSL client certificate without having to issue a token.

Prerequisites
-------------
Keystone must be running in a web container with https enabled; tests have
been done with Apache. Certificate and key management are outside the scope
of this document.

--------------------
Apache Configuration
--------------------

Make sure to enable SSL and have client authentication set to optional in
the Apache virtual file. Setting ``SSLVerifyClient`` to be ``optional`` to
allow other token authentication methods. For example:

.. code-block:: javascript

    SSLEngine on
    SSLCertificateFile    /etc/apache2/ssl/apache.crt
    SSLCertificateKeyFile /etc/apache2/ssl/apache.key
    SSLCACertificatePath /capath
    SSLVerifyClient optional

----------------------
Keystone Configuration
----------------------
The following configurable options can be defined in keystone.conf.

    * ``trusted_issuer``
        The list of trusted issuers to further filter the certificates
        that are allowed to participate in the X.509 tokenless authorization.
        If the option is absent then no certificates will be allowed. The
        naming format for the attributes of a Distinguished Name(DN) must
        be separated by a comma and contain no spaces. This configuration
        option may be repeated for multiple values. For example::
        trusted_isser=CN=john,OU=keystone,O=openstack
        trusted_isser=CN=mary,OU=eng,O=abc
    * ``protocol``
        The protocol name for the X.509 tokenless authorization along with
        the IdP name to look up its corresponding mapping. It defaults to
        ``x509``.
    * ``issuer_attribute``
        The issuer attribute that is served as an IdP for the X.509 tokenless
        authorization along with the protocol to look up its corresponding
        mapping. It is the attribute name in the WSGI enviornment that
        references to the Issuer of the client certificate. It defaults to
        ``SSL_CLIENT_I_DN``.
    * ``ephemeral_user``
        If this option is ``true``, the user referenced from the client
        certificate CN does not need to exist. A group needs to be defined
        in the corresponding mapping and this ephemeral user will have the
        same roles as what are assigned to the group. It defaults to
        ``false``.

-------------
Setup Mapping
-------------
Like federation, X.509 tokenless authorization also utilizes the mapping
mechanism to formulate an identity. The identity provider must correspond
to the issuer of the X.509 SSL client certificate. The protocol for the
given identity should be ``x509`` by default but can be configurable.

Create an IdP
-------------

The name of the IdP will need to be created from the client issuer DN and
it should contain no spaces. The following is the python code used to
create the IdP name.

.. code-block:: python

    hashed_idp = hashlib.sha256(idp_name)
    base64.b64encode(hashed_idp.digest())

Create a Protocol
-----------------

The name of the protocol will be the one defined in keystone.conf as protocol
which defaults to ``x509``.

Create a Map
------------

A user can be found based on the local mapping attributes, user_id or
user_name, domain_id or domain_name. And the remote mapping attributes can
be any of the client certificate attributes. For example:

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

When ``ephemeral_user`` is used, a valid group Id needs to be defined in
the map. For example:

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

---------------------------------------
Setup auth_token middleware
---------------------------------------

Configurable Options
---------------------
The following configurable options in ``auth_token`` middleware
should set to the correct values -

    * ``auth_protocol``
        Sets to ``https``.
    * ``certfile``
        Sets to the full path of the certifie file.
    * ``keyfile``
        Sets to the full path of the private key file.
    *  ``cafile``
        Sets to the full path of the trusted CA certificate file.

Scope Information
-----------------
The scope information will be passed from the headers with the following
keywords to:

    * ``X-Project-Id``
        If specified, its the project scope.
    * ``X-Project-Name``
        If specified, its the project scope.
    * ``X-Project-Domain-Id``
        If specified, its the project scope.
    * ``X-Project-Domain-Name``
        If specified, its the project scope.
    * ``X-Domain-Id``
        If specified, its the domain scope.
    * ``X-Domain-Name``
        If specified, its the domain scope.
