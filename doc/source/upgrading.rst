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

==================
Upgrading Keystone
==================

As of the Newton release, keystone supports two different approaches to
upgrading across releases. The traditional approach requires a significant
outage to be scheduled for the entire duration of the upgrade process. The more
modern approach requires zero downtime but limits the available capabilities of
the service during the upgrade process.

.. NOTE::

    The details of these steps are entirely dependent on the details of your
    specific deployment, such as your chosen application server and database
    management system. Use it only as a guide when implementing your own
    upgrade process!

Before you begin
----------------

Plan your upgrade:

* Read and ensure you understand the `release notes
  http://docs.openstack.org/releasenotes/keystone/`_ for the next release.

* Resolve any outstanding deprecation warnings in your logs. Some deprecation
  cycles are as short as a single release, so it's possible to break a
  deployment if you leave *any* outstanding warnings. It might be a good idea
  to re-read the release notes for the previous release (or two!).

* Prepare your new configuration files, including ``keystone.conf``,
  ``logging.conf``, ``policy.json``, ``keystone-paste.ini``, and anything else
  in ``/etc/keystone/``, by customizing the corresponding files from the next
  release.

Upgrading with downtime
-----------------------

This is a high-level description of our upgrade strategy built around
``keystone-manage db_sync``. It assumes that you are willing to have downtime
of your control plane during the upgrade process and presents minimal risk.
With keystone unavailable, no other OpenStack services will be able to
authenticate requests, effectively preventing the rest of the control plane
from functioning normally.

#. Stop all keystone processes. If you only upgrade one node at a time,
   then you'll risk multiple releases of keystone trying to write to the
   database at the same time.

#. Make a backup of your database. Keystone does not support downgrading the
   database, so restoring from a full backup is your only option for recovery
   in the event of an upgrade failure.

#. Upgrade all keystone nodes to the next release.

#. Update your configuration files (``/etc/keystone/``) with those
   corresponding from the latest release.

#. Run ``keystone-manage db_sync`` from any one node to upgrade both the
   database schema and run any corresponding database migrations.

#. (*New in Newton*) Run ``keystone-manage doctor`` to diagnose symptoms of
   common deployment issues and receive instructions for resolving them.

#. Start all keystone processes.

Upgrading without downtime
--------------------------

This is a high-level description of our upgrade strategy built around
``keystone-manage upgrade``. Although it is much more complex than the upgrade
process described above, it assumes that you are not willing to have downtime
of your control plane during the upgrade process. With this upgrade process,
end users will still be able to authenticate to receive Fernet tokens (other
token providers will experience an outage), and other OpenStack services will
still be able to authenticate requests normally.

However, in order to achieve zero downtime upgrades, keystone's API
capabilities *are* limited for the duration of the upgrade, resulting in a
partial service outage. API operations which require write access to the
database, such as creating users, changing passwords, and managing role
assignments will fail with HTTP error ``503 Service Unavailable`` for a portion
of the upgrade process.

#. Make a backup of your database. Keystone does not support downgrading the
   database, so restoring from a full backup is your only option for recovery
   in the event of an upgrade failure.

#. Stop the keystone processes on the first node (or really, any arbitrary
   node). This node will serve to orchestrate database upgrades.

#. Upgrade your first node to the next release, but do not start any keystone
   processes.

#. Update your configuration files on the first node (``/etc/keystone/``) with
   those corresponding to the latest release.

#. (*New in Newton*) Run ``keystone-manage doctor`` on the first node to
   diagnose symptoms of common deployment issues and receive instructions for
   resolving them.

#. Run ``keystone-manage upgrade --expand`` on the first node to expand the
   database schema to a superset of what both the previous and next release can
   read from.

   At this point, new columns and tables may exist in the database, but will
   not be populated in such a way that the next release will be able to
   function normally.

#. Set ``[DEFAULT] read_only_mode = true`` (*New in Newton*) in the
   ``keystone.conf`` files on all nodes, except the first one. Restart nodes
   one at a time so that the new configuration can take effect.

   When upgrading from Mitaka, which does not support ``[DEFAULT]
   read_only_mode``, you can instead take away keystone's write permission to
   the database. This will result in write operations failing with a less
   graceful HTTP error ``500 Internal Server Error``. Consider creating an
   alternate, read-only database user to use in keystone's ``[database]
   connection`` string instead of the ``[DEFAULT] read_only_mode`` option.

   At this point, keystone's API capabilities are limited, and no write
   operations are going to the database.

#. Run ``keystone-manage upgrade --migrate`` on the first node to perform data
   migrations.

   Without read-only mode in effect, the service might be racing the data
   migration process to create data in the old schema without also creating it
   in the corresponding new schema.

   At this point, the previous release may continue to read from the old schema
   and but it is also available to be read in the new schema.

#. Update your configuration files (``/etc/keystone/``) on all nodes (except
   the first node, which you've already done) with those corresponding to the
   latest release.

   Be sure to preserve ``[DEFAULT] read_only_mode = true``.

#. Upgrade all keystone nodes to the next release, and restart them one at a
   time. During this step, you'll have a mix of releases operating side by
   side, but neither will be writing to the database.

   Without read-only mode in effect on the nodes running the next release, data
   written by the next release may be read back differently than it would be by
   nodes still running the previous release.

#. Set ``[DEFAULT] read_only_mode = false`` in the ``keystone.conf`` files on
   all nodes, and restart them one at a time.

   At this point, all nodes are running the latest release and are allowed to
   write to the database again.

#. Run ``keystone-manage upgrade --contract`` to remove the old schema.
