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

=========================
Keystone Security Details
=========================

General
=======

This page documents security related details for the Keystone project.

Implemented Crypto
==================

None.

Used Crypto
===========

Libraries
~~~~~~~~~

* oauthlib (uses hashlib)
* OpenSSL
* PassLib
* PyCrypto
* hashlib
* python-ldap (ultimately uses GnuTLS, NSS, or OpenSSL depends on platform)
* requests (for keystoneclient HTTPS usage - need to investigate underlying
  crypto usage)

Encryption Algorithms
~~~~~~~~~~~~~~~~~~~~~

* Memcache backend encryption

 * Algorithm: AES
 * Configurable: No
 * Implementation: PyCrypto
 * Source:

  * keystoneclient/middleware/memcache_crypt.py

 * Details:

  * Optionally used for encrypting the token backend.

* PKI token signing

 * Algorithm: RSA
 * Configurable: Yes
 * Implementation: OpenSSL
 * Source:

  * keystone/common/openssl.py
  * keystoneclient/common/cms.py

 * Details:

  * 2048, sha1 defaults
  * Configurable via openssl.conf.
  * Keys/Certs can be created outside of Keystone and dropped in.

Hashing Algorithms
~~~~~~~~~~~~~~~~~~

* Token hashing

 * Algorithm: md5
 * Configurable: No
 * Implementation: hashlib
 * Source:

  * keystoneclient/utils.py
  * keystoneclient/common/cms.py

 * Details:

  * Hash is used as an internal identifier in the token backend.
  * The data being hashed is the entire cryptographically signed token
    (which uses the configured signing key). The chance for collisions
    should be low.

* S3 credentials

 * Algorithm: md5
 * Configurable: No
 * Implementation: hashlib

 * Source:

  * keystone/contrib/s3/core.py

 * Details:

  * Used for signature validation of S3 credentials.
  * Required for S3 compatibility, so it can't be configurable.

* LDAP password hashing

 * Algorithm: md5
 * Configurable: No
 * Implementation: PassLib

 * Source:

  * keystone/common/utils.py

 * Details:

  * Salted using PassLib default (currently 4 bytes).

* OAuth1

 * Algorithm: sha1
 * Configurable: No
 * Implementation: oauthlib

 * Source:

  * keystone/contrib/oauth1/core.py
  * keystone/contrib/oauth1/verifier.py

 * Details:

  * Used for signature validation of OAuth1 tokens.
  * Keystone only uses the HMAC*SHA1 signature for OAuth1 tokens
    (as described in RFC 5849).
  * OAuth support can be disabled.

* EC2 tokens

 * Algorithm: sha256
 * Configurable: No
 * Implementation: hashlib

 * Source:

  * keystone/credential/controllers.py
  * keystone/common/utils.py
  * keystoneclient/contrib/ec2/utils.py

 * Details:

  * Required for EC2 compatibility, so it can't be configurable.

* Memcache signing

 * Algorithm: sha384
 * Configurable: No
 * Implementation: hashlib

 * Source:

  * keystoneclient/middleware/memcache_crypt.py

 * Details:

  * Used for signing and verification when memcache encryption is
    enabled.

* Password hashing

 * Algorithm: sha512
 * Configurable: No
 * Implementation: PassLib

 * Source:

  * keystone/common/utils.py

 * Details:

  * The algorithm is non-configurable, but the number of rounds is
    configurable via CONF.crypt_strength (default=40000).

Sensitive Data
==============

Keys/Certificates
~~~~~~~~~~~~~~~~~

* PKI signing key - Protected via filesystem ownership/permissions.
* SSL/TLS key - Protected via filesystem ownership/permissions.

Passwords
~~~~~~~~~

* SSL/TLS must be enabled in Keystone to prevent clients from sending 
  passwords over the network in clear-text.
* Passwords are truncated to a maximum length prior to hashing

 * Configurable via CONF.identity.max_password_length (default=4096)

* SQL Identity

 * Password hashes are stored in SQL database.
 * SSL/TLS can be used to protect the connection to the database.

* LDAP Identity

 * SSL/TLS must be used for connections to LDAP to prevent Keystone from
   sending passwords over the network in clear-text.

Tokens
~~~~~~

* Signed tokens are stored in their entirety in one of the following backends:

 * KVS
 * Memcached

  * Ephemeral storage.
  * Able to use AES encryption and sha384 signing.

 * SQL (default)

  * Persistent storage.
  * SSL/TLS can be used to protect the connection to the database.

* Expired tokens are not automatically removed from the backend. The 
  `keystone-manage token_flush` command should be used to periodically
  remove expired tokens (via cron).

Potential Improvements
======================

* Eliminate LDAP user password hashing. This code should be unnecessary, as
  passwords supplied by clients should only be used to perform LDAP bind
  operations and never stored locally in any form.
* Allow all hashing schemes to be configurable where not restricted by
  compatibility requirements (such as S3 and EC2)
* The use of md5 for token hashing is the biggest concern, as it's use is
  discouraged (or disallowed in the case of FIPS). Changes are in progress
  to make this configurable in Juno. The default should be sha256 if possible.
* Allow support for LDAP SASL bind methods(such as DIGEST-MD5 and GSSAPI).
* Allow other forms of external authentication to avoid using passwords
  (Kerberos, SAML).
  