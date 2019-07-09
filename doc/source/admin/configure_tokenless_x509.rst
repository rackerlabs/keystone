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

  This feature is designed to reduce the complexity of user token validation
  in Keystone auth_token middleware by eliminating the need for service
  user token for authentication and authorization. Therefore, there's no need
  to having to create and maintain a service user account for the sole purpose
  of user token validation. Furthermore, this feature improves efficiency by
  avoiding service user token handling (i.e. request, cache, and renewal).
  By not having to deal with service user credentials in the configuration
  files, deployers are relieved of the burden of having to protect the
  server user passwords throughout the deployment lifecycle. This feature also
  improve security by using X.509 certificate instead of password for
  authentication.

  For details, please refer to the specs
  `Tokenless Authorization with X.509 Client SSL Certificate`_

.. _`Tokenless Authorization with X.509 Client SSL Certificate`: https://specs.openstack.org/openstack/keystone-specs/specs/liberty/keystone-tokenless-authz-with-x509-ssl-client-cert.html

Prerequisites
-------------

This feature requires Keystone API proxy SSL terminator to validate the
incoming X.509 SSL client certificate and pass the certificate information
(i.e. subject DN, issuer DN, etc) to the Keystone application as part of the
request environment. At the time of this writing the feature has been tested
with either HAProxy or Apache as Keystone API proxy SSL terminator only.

The rest of this document required readers to familiar with:

* `Public Key Infrastructure (PKI) and certificate management`
* `SSL with client authentication`, or commonly known as two-way SSL
* `Public Key Infrastructure (PKI) and certificate management`
* `Apache SSL configuration`
* `HAProxy SSL configuration`

.. _`Public Key Infrastructure (PKI) and certificate management`: https://en.wikipedia.org/wiki/Public_key_infrastructure
.. _`SSL with client authentication`: https://tools.ietf.org/html/rfc5246#section-7.4.6
.. _`Apache SSL configuration`: https://httpd.apache.org/docs/trunk/mod/mod_ssl.html#ssloptions
.. _`HAProxy SSL configuration`: http://cbonte.github.io/haproxy-dconv/1.7/configuration.html#7.3.4

Configuring this feature requires `OpenSSL Command Line Tool (CLI)`_. Please refer
to the respective OS installation guide on how to install it.

.. _`OpenSSL Command Line Tool (CLI)`: https://www.openssl.org/docs/manmaster/man1/openssl.html

----------------------
Keystone Configuration
----------------------

This feature utilizes Keystone federation capability to determine the
authorization associated with the incoming X.509 SSL client certificate by
mapping the certificate attributes to a Keystone identity. Therefore, the
direct issuer or trusted Certification Authority (CA) of the client certificate
is the remote Identity Provider (IDP), and the hexadecimal output of the SHA256
hash of the issuer distinguished name (DN) is used as the IDP ID.

.. NOTE::

   Client certificate issuer DN may be formatted differently depending on the
   SSL terminator. For example, Apache mod_ssl may use `RFC 2253` while HAProxy
   may use the old format. The old format is used by applications that linked
   with an older version of OpenSSL where the string representation of the
   distinguished name has not yet become a de facto standard. For more
   information on the old formation, please see the `nameopt` in the
   OpenSSL CLI manual. Therefore, it is critically important to keep the
   format consistent throughout the configuration as Keystone does exact string
   match when comparing Certificate attributes.

.. _`nameopt`: https://www.openssl.org/docs/manmaster/man1/x509.html
.. _`RFC 2253`: https://tools.ietf.org/html/rfc2253

How to obtain trusted issuer DN
-------------------------------
If SSL terminates at either HAProxy or Apache, the client certificate issuer
DN can be obtained by using the OpenSSL CLI.

Since version 2.3.11, Apache mod_ssl by default uses RFC 2253 when handling
certificate distinguished names. However, deployer have the option to use
the old format by configuring the ``LegacyDNStringFormat`` option.

.. _`LegacyDNStringFormat`: https://httpd.apache.org/docs/trunk/mod/mod_ssl.html#ssloptions

HAProxy, on the other hand, only supports the old format.

To obtain issuer DN in RFC 2253 format:

.. code-block:: bash

   $ openssl x509 -issuer -noout -in client_cert.pem -nameopt rfc2253 | sed 's/^\s*issuer=//'

To obtain issuer DN in old format:

.. code-block:: bash

   $ openssl x509 -issuer -noout -in client_cert.pem -nameopt compat | sed 's/^\s*issuer=//'

How to calculate the IDP ID from trusted issuer DN
--------------------------------------------------
The hexadecimal output of the SHA256 hash of the trusted issuer DN is being
used as the Identity Provider ID in Keystone. It can be obtained using
OpenSSL CLI.

To calculate the IDP ID for issuer DN in RFC 2253 format:

.. code-block:: bash

   $ openssl x509 -issuer -noout -in client_cert.pem -nameopt rfc2253 | tr -d '\n' | sed 's/^\s*issuer=//' | openssl dgst -sha256 -hex | awk '{print $2}'

To calculate the IDP ID for issuer DN in old format:

.. code-block:: bash

   $ openssl x509 -issuer -noout -in client_cert.pem -nameopt compat | tr -d '\n' | sed 's/^\s*issuer=//' | openssl dgst -sha256 -hex | awk '{print $2}'


Keystone Configuration File Changes
-----------------------------------

The following options in the ``tokenless_auth`` section of the Keystone
configuration file `keystone.conf` are used to enable the X.509 tokenless
authorization feature:

* ``trusted_issuer`` - A list of trusted issuers for the X.509 SSL client
  certificates. More specifically the list of trusted issuer DNs mentioned in
  the `How to obtain trusted issuer DN`_ section above.
  The format of the trusted issuer DNs must match exactly with what the SSL
  terminator passed into the request environment. For example, if SSL
  terminates in Apache mod_ssl, then the issuer DN should be in RFC 2253
  format. Whereas if SSL terminates in HAProxy, then the issuer DN
  is expected to be in the old format. This is a multi-string list option. The
  absence of any trusted issuers means the X.509 tokenless authorization
  feature is effectively disabled.
* ``protocol`` - The protocol name for the X.509 tokenless authorization
  along with the option `issuer_attribute` below can look up its
  corresponding mapping. It defaults to ``x509``.
* ``issuer_attribute`` - The issuer attribute that is served as an IdP ID for
  the X.509 tokenless authorization along with the protocol to look up its
  corresponding mapping. It is the environment variable in the WSGI
  environment that references to the Issuer of the client certificate. It
  defaults to ``SSL_CLIENT_I_DN``.

This is a sample configuration for two `trusted_issuer` and a `protocol` set
to ``x509``.

.. code-block:: ini

    [tokenless_auth]
    trusted_issuer = emailAddress=admin@foosigner.com,CN=Foo Signer,OU=eng,O=abc,L=San Jose,ST=California,C=US
    trusted_issuer = emailAddress=admin@openstack.com,CN=OpenStack Cert Signer,OU=keystone,O=openstack,L=Sunnyvale,ST=California,C=US
    protocol = x509

-------------
Setup Mapping
-------------

Like federation, X.509 tokenless authorization also utilizes the mapping
mechanism to formulate an identity. The identity provider must correspond
to the issuer of the X.509 SSL client certificate. The protocol for the
given identity is ``x509`` by default, but can be configurable.

Create an Identity Provider (IDP)
---------------------------------

As mentioned, the Identity Provider ID is the hexadecimal output of the SHA256
hash of the issuer distinguished name (DN).

.. NOTE::

   If there are multiple trusted issuers, there must be multiple IDP created,
   one for each trusted issuer.

To create an IDP for a given trusted issuer, follow the instructions in the
`How to calculate the IDP ID from trusted issuer DN`_ section to calculate
the IDP ID. Then use OpenStack CLI to create the IDP. i.e.

.. code-block:: bash

   $ openstack identity provider create --description 'IDP foo' <IDP ID>


Create a Map
------------

A mapping needs to be created to map the ``Subject DN`` in the client
certificate as a user to yield a valid local user if the user's ``type``
defined as ``local`` in the mapping. For example, the client certificate
has ``Subject DN`` as ``CN=alex,OU=eng,O=nice-network,L=Sunnyvale,
ST=California,C=US``, in the following examples, ``user_name`` will be
mapped to``alex`` and ``domain_name`` will be mapped to ``nice-network``.
And it has user's ``type`` set to ``local``. If user's ``type`` is not
defined, it defaults to ``ephemeral``.

Please refer to `mod_ssl`_ for the detailed mapping attributes.

.. _`mod_ssl`: http://httpd.apache.org/docs/current/mod/mod_ssl.html

.. code-block:: javascript

    [
        {
            "local": [
                {
                    "user": {
                        "name": "{0}",
                        "domain": {
                            "name": "{1}"
                        },
                        "type": "local"
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

When user's ``type`` is not defined or set to ``ephemeral``, the mapped user
does not have to be a valid local user but the mapping must yield at least
one valid local group. For example:

.. code-block:: javascript

    [
        {
            "local": [
                {
                    "user": {
                        "name": "{0}",
                        "type": "ephemeral"
                    },
                    "group": {
                        "domain": {
                            "name": "Default"
                        },
                        "name": "openstack_services"
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

.. NOTE::

   The above mapping assume openstack_services group already exist and have
   the proper role assignments (i.e. allow token validation) If not, it will
   need to be created.

To create a mapping using OpenStack CLI, assuming the mapping is saved into
a file ``x509_tokenless_mapping.json``:
.. code-block:: bash

   $ openstack mapping create --rules x509_tokenless_mapping.json x509_tokenless

.. NOTE::

   The mapping ID is arbitrary and it can be any string as opposed to
   IDP ID.

Create a Protocol
-----------------

The name of the protocol must be the same as the one specified by the
``protocol`` option in ``tokenless_auth`` section of the Keystone
configuration file. The protocol name is user designed and it can be any
name as opposed to IDP ID.

A protocol name and an IDP ID will uniquely identify a mapping.

To create a protocol using OpenStack CLI:

.. code-block:: bash

   $ openstack federation protocol create --identity-provider <IDP ID>
     --mapping x509_tokenless x509


.. NOTE::

   If there are multiple trusted issuers, there must be multiple protocol
   created, one for each IDP. All IDP can share a same mapping but the
   combination of IDP ID and protocol must be unique.

----------------------------
SSL Terminator Configuration
----------------------------

Apache Configuration
--------------------

If SSL terminates at Apache mod_ssl, Apache must be configured to handle
two-way SSL and pass the SSL certificate information to the Keystone
application as part of the request environment.

The Client authentication attribute ``SSLVerifyClient`` should be set
as ``optional`` to allow other token authentication methods and
attribute ``SSLOptions`` needs to set as ``+StdEnvVars`` to allow certificate
attributes to be passed. For example,

.. code-block:: ini

    <VirtualHost *:443>
        WSGIScriptAlias / /var/www/cgi-bin/keystone/main
        ErrorLog /var/log/apache2/keystone.log
        CustomLog /var/log/apache2/access.log combined
        SSLEngine on
        SSLCertificateFile    /etc/apache2/ssl/apache.cer
        SSLCertificateKeyFile /etc/apache2/ssl/apache.key
        SSLCACertificatePath /etc/apache2/capath
        SSLOptions +StdEnvVars
        SSLVerifyClient optional
    </VirtualHost>

HAProxy and Apache Configuration
--------------------------------
If SSL terminates at HAProxy and Apache is the API proxy for the Keystone
application, HAProxy must configured to handle two-way SSL and convey
the SSL certificate information via the request headers. Apache in turn will
need to bring those request headers into the request environment.

Here's an example on how to configure HAProxy to handle two-way SSL and
pass the SSL certificate information via the request headers.

.. code-block:: ini

    frontend http-frontend
        mode http
        option forwardfor
        bind 10.1.1.1:5000 ssl crt /etc/keystone/ssl/keystone.pem ca-file /etc/keystone/ssl/ca.pem verify optional

        reqadd X-Forwarded-Proto:\ https if { ssl_fc }
        http-request set-header X-SSL                   %[ssl_fc]
        http-request set-header X-SSL-Client-Verify     %[ssl_c_verify]
        http-request set-header X-SSL-Client-SHA1       %{+Q}[ssl_c_sha1]
        http-request set-header X-SSL-Client-DN         %{+Q}[ssl_c_s_dn]
        http-request set-header X-SSL-Client-CN         %{+Q}[ssl_c_s_dn(cn)]
        http-request set-header X-SSL-Client-O          %{+Q}[ssl_c_s_dn(o)]
        http-request set-header X-SSL-Issuer            %{+Q}[ssl_c_i_dn]
        http-request set-header X-SSL-Issuer-CN         %{+Q}[ssl_c_i_dn(cn)]

When the request gets to the Apache Keystone API Proxy, Apache will need to
bring those SSL headers into the request environment. Here's an example on
how to configure Apache to achieve that.

.. code-block:: ini

    <VirtualHost 192.168.0.10:5000>
        WSGIScriptAlias / /var/www/cgi-bin/keystone/main

        # Bring the needed SSL certificate attributes from HAProxy into the
        # request environment
        SetEnvIf X-SSL-Issuer "^(.*)$" SSL_CLIENT_I_DN=$0
        SetEnvIf X-SSL-Issuer-CN "^(.*)$" SSL_CLIENT_I_DN_CN=$0
        SetEnvIf X-SSL-Client-CN "^(.*)$" SSL_CLIENT_S_DN_CN=$0
        SetEnvIf X-SSL-Client-O "^(.*)$" SSL_CLIENT_S_DN_O=$0
    </VirtualHost>


-------------------------------
Setup ``auth_token`` middleware
-------------------------------

In order to use ``auth_token`` middleware as the service client for X.509
tokenless authorization, both configurable options and scope information
will need to be setup.

Configurable Options
--------------------

The following configurable options in ``auth_token`` middleware
should set to the correct values:


* ``auth_type`` - Must set to ``v3tokenlessauth``.
* ``certfile`` - Set to the full path of the certificate file.
* ``keyfile`` - Set to the full path of the private key file.
* ``cafile`` - Set to the full path of the trusted CA certificate file
* ``project_name`` or ``project_id`` - set to the scoped project
* ``project_domain_name`` or ``project_domain_id`` - if ``project_name`` is
  specified.

Here's an example of ``auth_token`` middleware configuration using X.509
tokenless authorization for user token validation.

.. code-block:: ini

    [keystone_authtoken]
    memcached_servers = localhost:11211
    cafile = /etc/keystone/ca.pem
    project_domain_name = Default
    project_name = service
    auth_url = https://192.168.0.10/identity/v3
    auth_type = v3tokenlessauth
    certfile = /etc/glance/certs/glance.pem
    keyfile = /etc/glance/private/glance_private_key.pem

