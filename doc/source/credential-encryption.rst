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

=====================
Credential Encryption
=====================

As of the Newton release, keystone encrypts all credentials stored in the
default ``sql`` backend. Credentials are encrypted with the same mechanism used
to encrypt Fernet tokens, ``fernet``. Keystone provides only one type of
credential encryption but the encryption provider is pluggable in the event
you wish to supply a custom implementation.

This document details how credential encryption works, how to migrate existing
credentials in a deployment, and how to manage encryption keys for credentials.

Configuring credential encryption
=================================

The configuration for credential encryption is straight-forward. There are only
two configuration options needed:

.. code-block:: ini

    [credential]
    provider = fernet
    key_repository = /etc/keystone/credential-keys/

``[credential] provider`` defaults to the only option supplied by keystone,
``fernet``. There is no reason to change this option unless you wish to provide
a custom credential encryption implementation. The ``[credential]
key_repository`` location is a requirement of using ``fernet`` but will default
to the ``/etc/keystone/credential-keys/`` directory. Is it recommended that
this location be changed to fit the needs of your deployment.  The purpose of
the ``[credential] key_repository`` is the same as ``[fernet_tokens]
key_repository``. One holds keys to encrypt and decrypt tokens and the other
holds keys to encrypt and decrypt credentials. These repositories should be
managed separately and should not share keys. ``[credential] key_repository``
will have a fixed number of keys available, three. This is not configurable and
allows for credentials to be re-keyed periodically with a new encryption key
for the sake of security.

How credential encryption works
===============================

The implementation of this feature did not change any existing credential API
contracts. All changes are transparent to the user unless you're inspecting the
credential backend directly.

When creating a credential, keystone will encrypt the ``blob`` attribute before
persisting it to the backend. Keystone will also store a 7 character hash of
the key that was used to encrypt the information in that credential. Since
Fernet is used to encrypt credentials, a key repository consists of multiple
keys. Keeping track of which key was used to encrypt each credential is an
important part of encryption key management. Why this is important is detailed
later in the `Encryption key management` section.

When updating an existing credential's ``blob`` attribute, keystone will encrypt
the new ``blob`` and update the key hash.

When listing or showing credentials, all ``blob`` attributes are decrypted in
the response. Neither the ciphertext, nor the hash of the key used to encrypt
the ``blob`` are exposed through the API. Furthermore, the key has is only used
internally to keystone.

Encrypting existing credentials
===============================

The encryption of existing plaintext credentials is done using the rolling
upgrade process. When upgrading a Mitaka deployment to Newton, three database
migrations will ensure all credentials are encrypted. The process is as
follows:

1. An additive schema change is made to create new ``encrypted_blob`` and
   ``key_hash`` columns in the existing ``credential`` table using
   ``keystone-manage db_sync --expand``.
2. A data migration will loop through all existing credentials, encrypt each
   ``blob`` and store the result in the new ``encrypted_blob`` column. The hash
   of the key used is also written to the ``key_hash`` column for that specific
   credential. This step is done using ``keystone-manage db_sync --migrate``.
3. A contractive schema will remove the ``blob`` column that held the plaintext
   representations of the credential using ``keystone-manage db_sync
   --contract``.

Note that a limited service outage will take affect during this migration. A
``[credential] key_repository`` location must be specified through
configuration and bootstrapped with keys using ``keystone-manage
credential_setup`` prior to migrating any existing credentials.  Credentials
will still be readable but no writes will be possible during the migration.
Once the schema has been contracted, it will be possible to create and update
credentials and all existing credentials should be encrypted.

Encryption key management
=========================

Key management of ``[credential] key_repository`` is handled with three
``keystone-manage`` commands:

1. ``keystone-manage credential_setup``
2. ``keystone-manage credential_rotate``
3. ``keystone-manage credential_migrate``

``keystone-manage credential_setup`` will populate ``[credential]
key_repository`` with new encryption keys. This must be done in order for
credential encryption to work. This is step should only need to be done once.

``keystone-manage credential_rotate`` will create and rotate a new encryption
key in the ``[credential] key_repository``. This will only be done if all
credential key hashes match the hash of the current primary key. If any
credential has been encrypted with an older key, or secondary key, the rotation
will fail. Failing the rotation is necessary to prevent over-rotation, which
would leave some credentials un-decipherable since the key used to encrypt it
no longer exists. If this step fails it is possible to forcibly re-key all
credentials using the same primary key with ``keystone-manage
credential_migrate``.

``keystone-manage credential_migrate`` will check the backend for credentials
whose key hash doesn't match the hash of the current primary key. Any
credentials with a key hash mismatching the current primary key will be
re-encrypted with the current primary key. The new ciphertext and key hash will
be updated in the backend.
