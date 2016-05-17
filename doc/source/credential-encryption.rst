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

Support encryption of credentials in Keystone to avoid having them stored in
plain text in the backend.

Fernet token keys are not a viable option as dedicated encryption keys for
credential encryption.  Token keys need to be rotated more often since tokens
are not persisted and are given to the user.  Credential encryption keys do not
need to be rotated as often because the encrypted credentials are not exposed
to the user.

Key rotation should be handled by doing the following:
- Add new fernet keys to ``encryption_keys`` on all keystone nodes.
- Update the active key on all keystone nodes.
- Use ``keystone-manage db_encrypt`` to re-encrypt existing credentials.

Configuring Encryption
======================

Credentials will not be encrypted by default.
To enable encryption update the ``[credential]`` section in ``keystone.conf``
add the list of fernet ``encryption_keys``.  The active key is the first key in
the list of ``encryption_keys``.  The active key is used for encrypting
credentials when adding and updating them.  All ``encryption_keys`` are used
for decryption of credentials.

To support credentials that were previously created without encryption,
``allow_plaintext`` can be set to true to allow decryption to return
non-encrypted credentials instead of throwing an error.  ``allow_plaintext``
should be set to ``false`` after all credentials are migrated using
``keystone_manage db_encrypt`` to catch encryption errors due to
misconfiguration.

Example configuration:

.. code-block:: ini

    [credential]
    encryption_keys = <fernet_key>,<fernet_key>
    allow_plaintext = True

Credential Migration
====================

All keystone nodes that access the backend should have the same configuration
with the ``encryption_keys`` value set before running the credential migration.
Once all keystone nodes are configured the credentials can be migrated with
the following command:

.. code-block:: bash

    $ keystone-manage db_encrypt

The above command will retrieve all credentials and re-encrypt them using the
current active key.
