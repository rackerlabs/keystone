..
      Copyright 2011-2012 OpenStack, LLC
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

==============================
Migrating from Diablo to Essex
==============================

This document describes the migration process from a Diablo-based deployment
to an Essex-based one. Because Keystone's first official release as an
OpenStack project is Essex, there are several potential migration paths that
you may need to consider.


Preparing Your Essex Deployment
===============================

Ensure Keystone is configured to use a SQL backend in your
``etc/keystone.conf``::

    [identity]
    driver = keystone.identity.backends.sql.Identity

Optionally, you may also want the default ``[sql]`` settings to better
reflect your environment::

    [sql]
    connection = sqlite:///openstack-keystone.db
    idle_timeout = 200
    min_pool_size = 5
    max_pool_size = 10
    pool_timeout = 200

You should now be ready to initialize your new database without error, using::

    $ keystone-manage db_sync

To test this, you should now be able to start ``keystone-all`` and use the
Keystone Client to list your tenants (which should successfully return an
empty list from your new database)::

    $ keystone --token ADMIN --endpoint http://127.0.0.1:35357/v2.0/ tenant-list
    +----+------+---------+
    | id | name | enabled |
    +----+------+---------+
    +----+------+---------+


Migrating From Keystone Diablo
==============================

The Essex release uses a completely new database backend as of Essex
Milestone 4, which means your old database schema will not be compatible, and
must be undergo a data migration.


Importing (almost) everything from Diablo
-----------------------------------------

Your Diablo-based deployment is backed by some type of SQL driver (Keystone
supports several, including SQLite, MySQL, PostgreSQL). This database must be
accessible by your new Essex deployment in order for Essex to import it.

Your old ``keystone.conf`` contains a SQL configuration section called
``[keystone.backends.sqlalchemy]`` connection string which, by default,
looks like::

    sql_connection = sqlite:///keystone.db

This connection string needs to be accessible from your Essex deployment (e.g.
you may need to copy your SQLite ``*.db`` file to a new server, adjust the
relative path as appropriate, or open a firewall for MySQL, etc).

Keystone Essex supports a special migration command, which you can now use
to import your legacy data::

    $ keystone-manage import_legacy <sql_connection>

You should now be able to run the same command you used to test your new
database above, but now you'll see your legacy Keystone data in Essex::

    $ keystone --token ADMIN --endpoint http://127.0.0.1:35357/v2.0/ tenant-list
    +----------------------------------+----------------+---------+
    |                id                |      name      | enabled |
    +----------------------------------+----------------+---------+
    | 12edde26a6224199a66ece67b762a065 | project-y      | True    |
    | 593715ed4359404999915ea7005a7da1 | ANOTHER:TENANT | True    |
    | be57fed798b049bc9637d2be30bfa857 | coffee-tea     | True    |
    | e3c382f4757a4385b502056431763cca | customer-x     | True    |
    +----------------------------------+----------------+---------+


Importing Service Catalog from Diablo
-------------------------------------

In Essex, your Service Catalog is not stored in a database, so you can't simply
directly import it. Instead, it's written as a flat ``template_file`` and
referenced from your ``keystone.conf`` as follows::

    [catalog]
    driver = keystone.catalog.backends.templated.TemplatedCatalog
    template_file = /etc/default_catalog.templates

If you're migrating from Diablo, you don't have to write this new file from
scratch. As before, point Keystone Essex at your Diablo database to build an
Essex-friendly service catalog automatically::

    $ keystone-manage export_legacy_catalog <sql_connection>
    catalog.RegionOne.object-store.internalUrl = http://127.0.0.1:8080/v1/AUTH_$(tenant_id)s
    catalog.RegionOne.object-store.publicUrl = http://swift.publicinternets.com/v1/AUTH_$(tenant_id)s
    catalog.RegionOne.object-store.adminUrl = http://swift.admin-nets.local:8080/
    catalog.RegionOne.object-store.enabled = 1
    catalog.RegionOne.object-store.name = Swift-compatible service
    catalog.RegionOne.compute.internalUrl = http://localhost:8774/v1.0
    catalog.RegionOne.compute.publicUrl = http://nova.publicinternets.com/v1.0/
    catalog.RegionOne.compute.adminUrl = http://127.0.0.1:8774/v1.0
    catalog.RegionOne.compute.enabled = 1
    catalog.RegionOne.compute.name = OpenStack Compute Service
    catalog.RegionOne.image.internalUrl = http://127.0.0.1:9292/v1.1/
    catalog.RegionOne.image.publicUrl = http://glance.publicinternets.com/v1.1/
    catalog.RegionOne.image.adminUrl = http://nova.admin-nets.local/v1.1/
    catalog.RegionOne.image.enabled = 1
    catalog.RegionOne.image.name = OpenStack Image Service

You can redirect the result directly into your ``template_file``.


Migrating From Nova's Deprecated Auth
=====================================

If you previously used the ``use_deprecated-auth`` flag in your ``nova.conf``
(the default configuration in Diablo), you'll want to migrate your deprecated
auth database to Keystone Essex.

Import a dump of Nova authentication data directly into Keystone Essex using::

    $ keystone-manage import_nova_auth <dump_file>
