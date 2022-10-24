===============================================
OAuth 2.0 Mutual-TLS Client Authentication Flow
===============================================
Overview
~~~~~~~~
OAuth 2.0 Mutual-TLS Client Authentication based on `RFC8705`_ is implemented
as an extension of Keystone. Users can use use_id as client_id to obtain the
OAuth 2.0 Certificate-Bound access token with TLS certificates. With the same
TLS certificates, the Certificate-Bound access token can then be used to access
the protected resources of the OpenStack API, which uses Keystone middleware
supporting the OAuth 2.0 Mutual-TLS Client Authentication. See the
`Identity API reference`_ for more information on generating OAuth 2.0 access
token.

Guide
~~~~~
Enable Keystone identity server to support OAuth 2.0 Mutual-TLS Client
Authentication by the following steps in this guide. In this example,
``keystone.host`` is the domain name used by the Keystone identity server.

.. _RFC8705: https://datatracker.ietf.org/doc/html/rfc8705
.. _`Identity API reference`: https://docs.openstack.org/api-ref/identity/v3/index.html#os-oauth2-api

Create a private/public Certificate Authority (CA)
--------------------------------------------------
In order to use mutual TLS, it is necessary to create a private/public
Certificate Authority (CA) as a root certificate that will be used to sign
client and keystone certificates.

1. Generate an RSA private key.

.. code-block:: console

    $ openssl genrsa -out root_a.key 4096
    Generating RSA private key, 4096 bit long modulus (2 primes)
    .++++
    .........................++++
    e is 65537 (0x010001)

2. Generate a self-signed certificate.

.. code-block:: console

    $ openssl req -new -x509 -key root_a.key -out root_a.pem -days 365
    You are about to be asked to enter information that will be incorporated
    into your certificate request.
    What you are about to enter is what is called a Distinguished Name or a DN.
    There are quite a few fields but you can leave some blank
    For some fields there will be a default value,
    If you enter '.', the field will be left blank.
    -----
    Country Name (2 letter code) [AU]: JP
    State or Province Name (full name) [Some-State]: Tokyo
    Locality Name (eg, city) []: Chiyoda-ku
    Organization Name (eg, company) [Internet Widgits Pty Ltd]: IssuingORG
    Organizational Unit Name (eg, section) []: CertDept
    Common Name (e.g. server FQDN or YOUR name) []: root_a.openstack.host
    Email Address []: root_a@issuing.org
    Please enter the following 'extra' attributes
    to be sent with your certificate request
    A challenge password []:
    An optional company name []:

3. If you need to support multiple root certificates, you can refer to step1
   and step2. Because of the needs of the server configuration, you need to
   merge these root certificates into a single file. Multiple root
   certificates are used in this guide, so another root certificate is
   created, the certificate is named root_b, and the CN of the certificate
   is "root_b.openstack.host".

.. code-block:: console

    $ cat root_a.pem >> multi_ca.pem
    $ cat root_b.pem >> multi_ca.pem
    $ cat multi_ca.pem
    -----BEGIN CERTIFICATE-----
    MIIF1TCCA72gAwIBAgIUN7d0MTiikDjDMLxUQ8SJcV97Nz8wDQYJKoZIhvcNAQEL
    BQAwejELMAkGA1UEBhMCSlAxEDAOBgNVBAgMB2ppYW5nc3UxDzANBgNVBAcMBnN1
    ...
    K/k00vZmrZXONglaf/OeMalhiRaOTsK2CzEvg6Xgu1zOjtNshm6qnSEXDYxzJue2
    FPLDGEMKSCLb
    -----END CERTIFICATE-----
    -----BEGIN CERTIFICATE-----
    MIIF1TCCA72gAwIBAgIUOiAEZWTheMS5wFA661G6bushkg4wDQYJKoZIhvcNAQEL
    BQAwejELMAkGA1UEBhMCY24xEDAOBgNVBAgMB2ppYW5nc3UxDzANBgNVBAcMBnN1
    ...
    UzvplIZcNZKzgOLLrSkk42/yqxdTZnc3BeBiVsA5T6aapNbY8D6ZpPU2cYYSxrfK
    VpOanJoJy22J
    -----END CERTIFICATE-----

Enable Keystone to support mutual TLS
-------------------------------------
The following parts describe steps to enable mutual TLS only for os-oauth2-api.

1. Generate an RSA private key.

.. code-block:: console

    $ openssl genrsa -out keystone_priv.key 4096
    Generating RSA private key, 4096 bit long modulus (2 primes)
    .........................................+++++
    .........................+++++
    e is 65537 (0x010001)

2. Create a certificate signing request.

.. code-block:: console

    $ openssl req -new -key keystone_priv.key -out keystone_csr.csr
    You are about to be asked to enter information that will be incorporated
    into your certificate request.
    What you are about to enter is what is called a Distinguished Name or a DN.
    There are quite a few fields but you can leave some blank
    For some fields there will be a default value,
    If you enter '.', the field will be left blank.
    -----
    Country Name (2 letter code) [AU]: JP
    State or Province Name (full name) [Some-State]: Tokyo
    Locality Name (eg, city) []: Chiyoda-ku
    Organization Name (eg, company) [Internet Widgits Pty Ltd]: OpenstackORG
    Organizational Unit Name (eg, section) []: DevDept
    Common Name (e.g. server FQDN or YOUR name) []:keystone.host
    Email Address []: dev@keystone.host
    Please enter the following 'extra' attributes
    to be sent with your certificate request
    A challenge password []:
    An optional company name []:

3. Use the root certificate to generate a self-signed certificate.

.. code-block:: console

    $ openssl x509 -req -in keystone_csr.csr \
    -CA root_a.pem -CAkey root_a.key -CAcreateserial \
    -out keystone_ca.pem -days 365 -sha384
    Signature ok
    subject=C = JP, ST = Tokyo, L = Chiyoda-ku, O = OpenstackORG, OU = DevDept, CN = keystone.host, emailAddress = dev@keystone.host
    Getting CA Private Key

4. Modify the apache configuration file and add options to implement mutual TLS
   support for the Keystone service.

.. code-block:: console

    $ sudo vi /etc/apache2/sites-enabled/keystone-wsgi-public.conf
    ProxyPass "/identity" "unix:/var/run/uwsgi/keystone-wsgi-public.socket|uwsgi://uwsgi-uds-keystone-wsgi-public" retry=0
    <IfModule mod_ssl.c>
    <VirtualHost _default_:443>
      ServerAdmin webmaster@localhost
      ErrorLog ${APACHE_LOG_DIR}/error.log
      CustomLog ${APACHE_LOG_DIR}/access.log combined
      SSLEngine on
      SSLCertificateFile      /etc/ssl/certs/keystone_ca.pem
      SSLCertificateKeyFile   /etc/ssl/private/keystone_priv.key
      SSLCACertificateFile    /etc/ssl/certs/multi_ca.pem
      <Location /identity/v3/OS-OAUTH2/token>
        SSLVerifyClient require
        SSLOptions +ExportCertData
        SSLOptions +StdEnvVars
        SSLRequireSSL
      </Location>
    </VirtualHost>
    </IfModule>

5. Restart apache service so that the modified configuration information takes
   effect.

.. code-block:: console

    $ systemctl restart apache2.service
    ==== AUTHENTICATING FOR org.freedesktop.systemd1.manage-units ===
    Authentication is required to restart 'apache2.service'.
    Authenticating as: Ubuntu (ubuntu)
    Password:
    ==== AUTHENTICATION COMPLETE ===

Create mapping rules for validating TLS certificates
----------------------------------------------------
Because different root certificates have different ways of authenticating TLS
certificates provided by client, the relevant mapping rules need to be set in
the system.

1. Create a mapping rule file. The mapping used below supports both root
   certificates. When the CN name of the issuer of the client certificate is
   "root_a.openstack.host", the client certificate must contain the 5 fields
   specified by Mapping, and these fields must match the user information in
   Keystone. When the CN name of the issuer of the client certificate is
   "root_b.openstack.host", only 2 fields need to be included to keep the
   user information consistent with the keystone. When using Subject
   Distinguished Names, the "SSL_CLIENT_SUBJECT_DN_*" format must be used.
   When using Issuer Distinguished Names, the "SSL_CLIENT_ISSUER_DN_*" format
   must be used. The "*" part is the key of the attribute for Distinguished
   Names converted to uppercase. For more information about the attribute
   types for Distinguished Names, see the relevant RFC documentation
   such as: `RFC1779`_, `RFC2985`_, `RFC4519`_, etc.

.. code-block:: console

    $ vi oauth2_mapping.json
    [
      {
        "local": [
          {
            "user": {
              "name": "{0}",
              "id": "{1}",
              "email": "{2}",
              "domain": {
                "name": "{3}",
                "id": "{4}"
              }
            }
          }
        ],
        "remote": [
          {
            "type": "SSL_CLIENT_SUBJECT_DN_CN"
          },
          {
            "type": "SSL_CLIENT_SUBJECT_DN_UID"
          },
          {
            "type": "SSL_CLIENT_SUBJECT_DN_EMAILADDRESS"
          },
          {
            "type": "SSL_CLIENT_SUBJECT_DN_O"
          },
          {
            "type": "SSL_CLIENT_SUBJECT_DN_DC"
          },
          {
            "type": "SSL_CLIENT_ISSUER_DN_CN",
            "any_one_of": [
                "root_a.openstack.host"
           ]
          }
        ]
      },
      {
        "local": [
          {
            "user": {
              "id": "{0}",
               "domain": {
                "id": "{1}"
              }
            }
          }
        ],
        "remote": [
          {
            "type": "SSL_CLIENT_SUBJECT_DN_UID"
          },
          {
            "type": "SSL_CLIENT_SUBJECT_DN_DC"
          },
          {
            "type": "SSL_CLIENT_ISSUER_DN_CN",
            "any_one_of": [
                "root_b.openstack.host"
           ]
          }
        ]
      }
    ]

2. Use the file to create the mapping rule in keystone.

.. code-block:: console

    $ openstack mapping create --rules oauth2_mapping.json oauth2_mapping

3. If it already exists, use the file to update the mapping rule in keystone.

.. code-block:: console

    openstack mapping set --rules oauth2_mapping.json oauth2_mapping

.. _RFC1779: https://datatracker.ietf.org/doc/html/rfc1779
.. _RFC2985: https://datatracker.ietf.org/doc/html/rfc2985
.. _RFC4519: https://datatracker.ietf.org/doc/html/rfc4519

Enable keystone to support OAuth 2.0 Mutual-TLS Client Authentication
---------------------------------------------------------------------
Modify the relevant configuration to enable the os-oauth2-api to use TLS
certificates for user authentication.

1. Modify ``keystone.conf`` to OAuth 2.0 Mutual-TLS Client Authentication.

.. code-block:: console

    $ vi /etc/keystone/keystone.conf
    [oauth2]
    oauth2_authn_method = certificate
    oauth2_cert_dn_mapping_id=oauth2_mapping

2. Restart Keystone service so that the modified configuration information
   takes effect.

.. code-block:: console

    $ sudo systemctl restart devstack@keystone.service

Try to access the Keystone APIs
-------------------------------
At last, try to access the Keystone APIs to confirm that the server is working
properly.

1. Create an OAuth 2.0 Mutual-TLS Client Authentication user. Because some
OpenStack APIs require project information, it is recommended to specify the
project when creating a user.

.. code-block:: console

    $ openstack user create --domain default --email test@testproject.com --project demo --project-domain default project_user
    +---------------------+----------------------------------+
    | Field               | Value                            |
    +---------------------+----------------------------------+
    | default_project_id  | e100040740a3459d9225b4a6b45bb54a |
    | domain_id           | default                          |
    | email               | test@demo.com                    |
    | enabled             | True                             |
    | id                  | 12d31647289c45e1b69e57273fce78b4 |
    | name                | client01                         |
    | options             | {}                               |
    | password_expires_at | None                             |
    +---------------------+----------------------------------+

2. Existing users can set the project information through the command.

.. code-block:: console

    $ openstack user show dc121fe98acd48aeb042f8f554567126
    +---------------------+----------------------------------+
    | Field               | Value                            |
    +---------------------+----------------------------------+
    | domain_id           | default                          |
    | enabled             | True                             |
    | id                  | dc121fe98acd48aeb042f8f554567126 |
    | name                | client02                         |
    | options             | {}                               |
    | password_expires_at | None                             |
    +---------------------+----------------------------------+
    $ openstack user set dc121fe98acd48aeb042f8f554567126 --project e100040740a3459d9225b4a6b45bb54a
    $ openstack user show dc121fe98acd48aeb042f8f554567126
    +---------------------+----------------------------------+
    | Field               | Value                            |
    +---------------------+----------------------------------+
    | default_project_id  | e100040740a3459d9225b4a6b45bb54a |
    | domain_id           | default                          |
    | enabled             | True                             |
    | id                  | dc121fe98acd48aeb042f8f554567126 |
    | name                | client02                         |
    | options             | {}                               |
    | password_expires_at | None                             |
    +---------------------+----------------------------------+

3. Assign roles to the user.

.. code-block:: console

    $ openstack role add --project e100040740a3459d9225b4a6b45bb54a --user 12d31647289c45e1b69e57273fce78b4 admin
    $ openstack role assignment list --user 12d31647289c45e1b69e57273fce78b4 --project e100040740a3459d9225b4a6b45bb54a
    +----------------------------------+----------------------------------+-------+----------------------------------+--------+--------+-----------+
    | Role                             | User                             | Group | Project                          | Domain | System | Inherited |
    +----------------------------------+----------------------------------+-------+----------------------------------+--------+--------+-----------+
    | 8c3f16960bd14abe9a42e6fa6673ab3c | 12d31647289c45e1b69e57273fce78b4 |       | e100040740a3459d9225b4a6b45bb54a |        |        | False     |
    +----------------------------------+----------------------------------+-------+----------------------------------+--------+--------+-----------+
    $ openstack role add --project e100040740a3459d9225b4a6b45bb54a --user dc121fe98acd48aeb042f8f554567126 admin
    $ openstack role assignment list --user dc121fe98acd48aeb042f8f554567126 --project e100040740a3459d9225b4a6b45bb54a
    +----------------------------------+----------------------------------+-------+----------------------------------+--------+--------+-----------+
    | Role                             | User                             | Group | Project                          | Domain | System | Inherited |
    +----------------------------------+----------------------------------+-------+----------------------------------+--------+--------+-----------+
    | 8c3f16960bd14abe9a42e6fa6673ab3c | dc121fe98acd48aeb042f8f554567126 |       | e100040740a3459d9225b4a6b45bb54a |        |        | False     |
    +----------------------------------+----------------------------------+-------+----------------------------------+--------+--------+-----------+

4. Generate an RSA private key for the user.

.. code-block:: console

    $ openssl genrsa -out client01_priv.key 4096
    Generating RSA private key, 4096 bit long modulus (2 primes)
    .........................................+++++
    .........................+++++
    e is 65537 (0x010001)
    $ openssl genrsa -out client02_priv.key 4096
    Generating RSA private key, 4096 bit long modulus (2 primes)
    .........................................+++++
    .........................+++++
    e is 65537 (0x010001)

5. Create a certificate signing request based on the mapping rule of the root
   certificate and on the user information. Because the client certificate is
   subsequently signed with root_a, five fields are specified when the request
   is created. If root_b is used to issue the client certificate, only two
   fields are required when creating the request.

.. code-block:: console

    $ openssl req -new -key client01_priv.key -out client01.csr \
    -subj "/UID=12d31647289c45e1b69e57273fce78b4/O=Default/DC=default/emailAddress=test@demo.com/CN=client01"
    $ openssl req -new -key client02_priv.key -out client02.csr \
    -subj "/UID=dc121fe98acd48aeb042f8f554567126/DC=default/CN=client02"

6. Use the root certificate to generate a self-signed certificate for the user.

.. code-block:: console

    $ openssl x509 -req -in client01.csr \
    -CA root_a.pem -CAkey root_a.key -CAcreateserial -out \
    client01.pem -days 180 -sha256
    Signature ok
    subject=UID = 12d31647289c45e1b69e57273fce78b4, O = Default, DC = default, emailAddress = test@demo.com, CN = client01
    Getting CA Private Key
    $ openssl x509 -req -in client02.csr \
    -CA root_b.pem -CAkey root_b.key -CAcreateserial -out \
    client02.pem -days 180 -sha256
    Signature ok
    subject=UID = dc121fe98acd48aeb042f8f554567126, DC = default, CN = client02
    Getting CA Private Key

7. Through the HTTP protocol, access the Keystone token API to confirm that the
   X-Auth-Token can be obtained normally.

.. code-block:: console

    $ curl -si -X POST http://keystone.local/identity/v3/auth/tokens?nocatalog \
    -d '{"auth":{"identity":{"methods":["password"],"password": {"user":{"domain":{"name":"Default"},"name":"username","password":"test_pwd"}}},"scope":{"project":{"domain":{"name":"Default"},"name":"admin"}}}}' \
    -H 'Content-type:application/json'
    HTTP/1.1 201 CREATED
    Date: Mon, 28 Feb 2022 08:50:31 GMT
    Server: Apache/2.4.41 (Ubuntu)
    Content-Type: application/json
    Content-Length: 648
    X-Subject-Token: $x_auth_token
    Vary: X-Auth-Token
    x-openstack-request-id: req-e84d2387-10c7-4bb9-942e-61190e9186d9
    Connection: close
    {"token": {"methods": ["password"], "user": {"domain": {"id": "default", "name": "Default"}, "id": "333e5ae19cbb47e8b18969306582be25", "name": "admin", "password_expires_at": null}, "audit_ids": ["SARKwdr8RmG4HKUhPXhItA"], "expires_at": "2022-10-08T02:55:48.000000Z", "issued_at": "2022-10-08T01:55:48.000000Z", "project": {"domain": {"id": "default", "name": "Default"}, "id": "6890f5679f304671aba65dfd4e9b11f5", "name": "admin"}, "is_domain": false, "roles": [{"id": "f74bd29b00b443efa44a57932961d410", "name": "reader"}, {"id": "8c3f16960bd14abe9a42e6fa6673ab3c", "name": "admin"}, {"id": "aa1952e4ff264da9bab8bdf93cac1e57", "name": "member"}]}}

8. Obtain OAuth 2.0 Certificate-Bound access tokens through OAuth 2.0
   Mutual-TLS Client Authentication.

.. code-block:: console

    $ curl -si -X POST https://keystone.local/identity/v3/OS-OAUTH2/token \
    -H "application/x-www-form-urlencoded" \
    -d "grant_type=client_credentials&client_id=12d31647289c45e1b69e57273fce78b4" \
    --cacert /home/test/root_a.pem \
    --key /home/test/client01_priv.key --cert /home/test/client01.pem
    HTTP/1.1 200 OK
    Date: Wed, 03 Aug 2022 01:28:39 GMT
    Server: Apache/2.4.41 (Ubuntu)
    Content-Type: application/json
    Content-Length: 328
    Vary: X-Auth-Token
    x-openstack-request-id: req-573e1978-f589-49dd-8784-bfb11fd4a2dc
    Connection: close
    {"access_token":"gAAAAABjKsA_3Z2U2sbgY_l6fDR8wqFORsm4x2f5XZ3_HKPRTBnmqyOS_7_YaJ14rBCb-vkp_F8O38nPfrzu2GYIa0D_pmBw3WCbf0dllgbmeMDMr1yx-Xd30lB5eTuhnFqusyeqlXUanMeGYNk8qlkUrSEoDrOEYG5yPPqPrJO92uF1tkklCQXLmCWSev5HlLet1dcTchFjR3F8s1E1P9dIYPLI61LbTEPHZUSePdnXqxVthWoGpapG85wRBc3jEETkQfTnDYsn","expires_in":3600,"token_type":"Bearer"}
    $ curl -si -X POST https://keystone.local/identity/v3/OS-OAUTH2/token \
    -H "application/x-www-form-urlencoded" \
    -d "grant_type=client_credentials&client_id=dc121fe98acd48aeb042f8f554567126" \
    --cacert /home/test/root_a.pem \
    --key /home/test/client02_priv.key --cert /home/test/client02.pem
    HTTP/1.1 200 OK
    Date: Wed, 03 Aug 2022 01:28:39 GMT
    Server: Apache/2.4.41 (Ubuntu)
    Content-Type: application/json
    Content-Length: 328
    Vary: X-Auth-Token
    x-openstack-request-id: req-990a87a8-ab02-4701-9adb-25dcd91fe3c9
    Connection: close
    {"access_token":"gAAAAABi6c9HZvUiaulp4xubmqwMkVkIJueDPrJinm7BvZxMMb9yWFkwWXXDEC407_u5o8DR9bqul0yKDEZzmzXoSe_P5Q_Adq30DCnHljRQtkfvzg33YZPtxOEQANUzs_sQBDTY7QBqRLwXxwm8xtqoPDOeG4SoZnLNcfUaxzaPDF6snVzfM5UOhfAzxa-SnzRk25vfiC_xJGIH6Zn8kNEspvs0-zGUKOUNt3rOrg5RmkYNQnemZbwDjfU9AkpB6V1ZDWL38Ijz","expires_in":3600,"token_type":"Bearer"}

9. Confirm that the OAuth 2.0 Certificate-Bound access tokens contain
   information such as project, roles, thumbprint, etc.

.. code-block:: console

    $ curl -si -X GET http://keystone.local/identity/v3/auth/tokens?nocatalog -H "X-Auth-Token:$x_auth_token" -H "X-Subject-Token:$access_token"
    HTTP/1.1 200 OK
    Date: Wed, 21 Sep 2022 07:42:41 GMT
    Server: Apache/2.4.41 (Ubuntu)
    Content-Type: application/json
    Content-Length: 5598
    X-Subject-Token: $access_token
    Vary: X-Auth-Token
    x-openstack-request-id: req-990a87a8-ab02-4701-9adb-25dcd91fe3c9
    Connection: close
    {"token": {"methods": ["oauth2_credential"], "user": {"domain": {"id": "default", "name": "Default"}, "id": "12d31647289c45e1b69e57273fce78b4", "name": "client01", "password_expires_at": null}, "audit_ids": ["bPTUs95iRCqnP7B2xNWf0Q"], "expires_at": "2022-10-08T03:03:21.000000Z", "issued_at": "2022-10-08T02:03:21.000000Z", "project": {"domain": {"id": "default", "name": "Default"}, "id": "da8aa10b994d4320b851a43f0f7abc86", "name": "test-project"}, "is_domain": false, "roles": [{"id": "f74bd29b00b443efa44a57932961d410", "name": "reader"}, {"id": "8c3f16960bd14abe9a42e6fa6673ab3c", "name": "admin"}, {"id": "aa1952e4ff264da9bab8bdf93cac1e57", "name": "member"}], "oauth2_credential": {"id": "12d31647289c45e1b69e57273fce78b4", "x5t#S256": "voNBNQTJ4xsuBb4CW-vXdbT93BfHnk0HThNhM-bR0WA="}}}
