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

.. WARNING::

    This feature is experimental and unsupported in Kilo.

-----------
Definitions
-----------
* ``X.509 Tokenless Authorization``
    Provides an althernative support for service clients to be authorized
    from Keystone by using a X.509 SSL client certificate without having
    to issue a token.

Prerequisites
-------------
Keystone will be required running in Apache with https enabled. Certificate
and key management are outside the scope of this document.

--------------------
Apache Configuration
--------------------

Make sure to enable SSL and have client authentication set to optional in
the Apache virtual file. For Example:

.. code-block:: javascript

    SSLEngine on
    SSLCertificateFile    /etc/apache2/ssl/apache.crt
    SSLCertificateKeyFile /etc/apache2/ssl/apache.key
    SSLCACertificatePath /capath
    SSLVerifyClient optional

----------------------
Keystone Configuration
----------------------
There are 3 configurable parameters can be defined in keystone.conf.

    * ``trusted_issuer``
        The list of trusted issuers is to further filter the certificates
        that are allowed to participate in the X.509 tokenless authorization.
        If it is absent, no certificates will be allowed in the X.509
        tokenless authorization. The value of an DN must be separated by a
        comma and contains no spaces. This configuration option may be
        repeated for multiple values. For example:
        ``trusted_isser=CN=john,OU=keystone,O=openstack``
        ``trusted_isser=CN=mary,OU=eng,O=abc``
    * ``protocol``
        The protocol name for the X.509 tokenless authorization along with
        the Idp name to look up its corresponding mapping. It defaults to 
        ``x509``.
    * ``issuer_attribute``
        The issuer attribute that is served as a IdP for the X.509 tokenless
        authorization along with the protocol to look up its corresponding
        mapping. It defaults to ``SSL_CLIENT_I_DN``.

-------------
Setup Mapping
-------------
Like federation, X.509 tokenless authorization also utilizes mapping
mechanism to formulate an indentity. The identity provider must be
corresponding to the issuer of the X.509 SSL client certificate. Protocol
for the given identity should be ``x509`` by default but can be configurable.

Create an Idp
-------------

The name of the IdP will need to be created from the client issuer DN and
it should contains no spaces. And the following is the python code used to
create the IdP name.

.. code-block:: ini

    hashed_idp = hashlib.sha256(idp_name)
    base64.b64encode(hashed_idp.digest())

Create a Protocol
-----------------

The name of the protocol will be the one defined in keystone.conf as protocol
which defaults to ``509``.

Create a Map
------------

An user can be found based on the local mapping attributes, user_id or
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
                            "type": "SSL_CLIENT_I_DN_O"
                        }
                    ]
                }
            ]
        }
    }

------------------------
Setup Keystonemiddleware
------------------------
The following configurable options in Keystonemiddle should set to the
correct values.

    * ``auth_protocol``
        Sets to ``https``.
    * ``certfile``
        Sets to the full path of the certifie file.
    * ``keyfile``
        Sets to the full path of the private key file.
    *  ``cafile``
        Sets to the full path of the trusted CA certificate file.
    * ``X-Project-Id``
        If specified, its the project scope passed through the headers.
    * ``X-Project-Name``
        If specified, its the project scope passed through the headers.
    * ``X-Project-Domain-Id``
        If specified, its the project scope passed through the headers.
    * ``X-Project-Domain-Name``
        If specified, its the project scope passed through the headers.
    * ``X-Domain-Id``
        If specified, its the domain scope passed through the headers.
    * ``X-Domain-Name``
        If specified, its the domain scope passed through the headers.
