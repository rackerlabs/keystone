..
      Copyright 2011-2012 OpenStack Foundation
      All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

      http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

===================================
Fernet - Frequently Asked Questions
===================================

The following questions have been asked periodically since the initial release
of the Fernet token format in Kilo.

What are the different types of keys?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A key repository is required by keystone in order to create Fernet tokens.
These keys are used to encrypt and decrypt the information that makes up the
payload of the token. Each key in the repository can have one of three states.
The state of the key determines how a key is used with Fernet tokens. The
different types are as follows:

* Primary Key: There is only ever one primary key in a key repository. The
  primary key is allowed to create and validate tokens. This key is always
  named as ``1`` in the key repository.
* Secondary Key: The secondary key was at one point a primary key, but has
  since been demoted in place of another primary. It is only allowed to
  validate tokens. Since it was the primary at some point in time, it existence
  in the key repository is justified because keystone needs the ability to
  validate tokens that were created with old primary keys. This key is always
  named higher than ``1`` in the key repository, since ``1`` is reserved for
  the primary key.
* Staged Key: The staged key is a special key that shares some similarities
  with secondary keys. Just like secondary keys, staged keys have the ability
  to validate tokens. Unlike secondary keys, staged keys have never been a
  primary key. In fact, they are opposites in that since because a staged key
  will always be the next primary key. This helps clarify the name they carry
  because they are the next key **staged** to be the primary key. This key is
  always named as ``0`` in the key repository.

So, how does a staged key help me and why do I care about it?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Fernet keys have a natural life-cycle. Each key starts as a staged key, is
promoted to be the primary key, and then demoted to the secondary key. Only the
primary key can actually create new keystone tokens but all key types can
validate tokens. The staged key is special given the order of events and the
attributes of each key. The staged key is the only key in the repository that
**hasn't** had a chance to create any tokens yet, but it's still allowed to
decrypt tokens. This gives operators the chance to perform a key rotation on
one keystone node, and distribute the new key set over a span of time. This
doesn't require the distribution to take place in an ultra short period of time
for fear of not being able to validate tokens created by a different node in
the cluster.

Where do I put my key repository?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``key_repository`` configuration option will tell keystone where to look
for keys. Currently, keystone only supports file-backed key repositories. By
default, the key repository lives in the keystone configuration directory but
it can be specified through keystone's configuration file:

..code-block:: ini

  [fernet_tokens]
  key_repository = /etc/keystone/fernet-keys/

What is the recommended way to rotate and distribute keys?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There is a key rotation mechanism built into the ``keystone-manage`` command
line utility. This mechanism only focuses on rotating keys and doesn't make an
effort to distribute keys across keystone nodes. The distribution of key across
a keystone deployment is best handled through configuration management tooling.

Do Fernet tokens still expires?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Yes, Fernet tokens can expires just like any of keystone's other token formats.

Why should I choose Fernet tokens over UUID tokens?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Even though Fernet tokens operate very similar to UUID tokens, they do not
require persistence. Meaning, the database no longer suffers bloat as a side
effect of authentication.

Why should I choose Fernet tokens over PKI or PKIZ tokens?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The arguments for using Fernet over PKI and PKIZ remain the same as UUID, in
addition to the fact that Fernet tokens are much smaller than PKI and PKIZ
tokens. PKI and PKIZ tokens still require persistent storage. However, Fernet
tokens can't be validated by the client. If you're leveraging distributed
signing for PKI and PKIZ tokens, you won't be able to continue that flow with
Fernet, simply because keystone doesn't share it's key repository with clients.

Must you rotate and distribute keys from the same keystone node every rotation?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

No, but the relationship between rotation and distribution should be lock-step.
Mean, once you rotate keys on one keystone node, the key repository from that
node should be distributed to the rest of the cluster. Once you confirm that
each node has the same key repository state, you could rotate and distribute
from any other node in the cluster.

How do I add new keystone nodes to a deployment?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The keys used to create Fernet tokens should be treated like super secret
configuration files. Before a node is allowed to join an existing cluster,
issuing and validating tokens, it should have the same key repository state as
the rest of the nodes in the cluster. This can be done by distributing the
current key repository from an existing node in the cluster.

How should I approach key distribution?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Remember that key distribution is only required in multi-node keystone
deployments. If you only have one keystone node serving requests in your
deployment distribution is unnecessary.

Key distribution is a problem best approached from the deployments current
configuration management system (i.e. ``ansible``, ``chef``, ``puppet``). Since
not all deployments use the same configuration management systems, it makes
sense to explore options around what is already available for managing keys,
while keeping the secrecy of the keys in mind.  Many of these tools can
leverage something like ``rsync`` to manage your key distribution.

Key rotation is a single operation that promotes the current staged key to
primary, creates a new staged key, and prunes old keys. It's easiest to do this
on a single node and verify the rotation took place properly before
distributing key repository to the rest of the cluster. The concept behind the
staged key breaks the expectation that key rotation and key distribution have
to be done in a single step. With the staged key, we have time to inspect the
new key repository before syncing state with the rest of the cluster. Key
distribution should be an operation that can run in succession until it
succeeds. The following might help illustrate the isolation and workflow
between key rotation and key distribution.

1. Ensure all keystone nodes in the deployment have the same key repository.
2. Pick a keystone node in the cluster to rotate from.
3. Rotate keys.
   a) Was is successful?
      i) If no, investigate issues with the particular keystone host you
         rotated keys on. Fernet keys are small and the operation for rotation
         is fairly trivial. There shouldn't be much room for error in key
         rotation.
      ii) If yes, you should see a new staged key, the old staged key should be
          the new primary, and depending on the ``max_active_keys`` limit you
          have set you might have keys that were pruned. At this point, the
          node that you rotated on will be creating Fernet tokens with a
          primary key that all other nodes should have. This is why we checked
          the state of all key repositories in Step 1. All other nodes in the
          cluster should be able decrypt tokens created with the new primary.
          At this point, we're ready to distribute the new key set.
4. Distribute the new key repository.
   a) Was it successful?
      i) If yes, you should be able to confirm that all nodes in the cluster
         have the same key repository state that was introduced in Step 3. Now
         all nodes in the cluster will be creating tokens with the primary key
         that was promoted in Step 3. Everything is good to go until the next
         schedule key rotation.
      ii) If no, try distributing again. Remember that we already rotated the
          repository and performing another rotation at this point will result
          in tokens that can't be validated across certain hosts. Specifically,
          the hosts that didn't get the latest key set. You should be able to
          execute distribution of keys until it's successful. If certain nodes
          have issues syncing, it could be permission or network issues and
          those should be resolved before subsequent rotations anyway.

How long should I keep my keys around?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The Fernet tokens that keystone creates are only secure as long as the keys
creating them. With staged keys the penalty of key rotation is low, allowing an
operator to err on the side of security and rotate weekly, daily, or even
hourly. Ultimately, this should be less time than it takes an attacker to break
a AES256 key and a SHA256 HMAC.

Is a Fernet token still a bearer token?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Yes, and they follow exactly the same validation path as ``uuid`` tokens, with
the exception of being persisted in a backend. If someone compromises your
Fernet token, they have the power to do all the operations you are allowed to
do.

What if I need to revoke all my tokens?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To invalidate every token issued from keystone and start fresh, remove the
current key repository, create a new key set, and redistribute it to all nodes
in the cluster. This will render every token issued from keystone as invalid
regardless if the token has actually expired. When a client goes to
re-authenticate, the new token will have been created with a new Fernet key.
