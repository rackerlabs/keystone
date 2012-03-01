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
to an Essex-based one.


Database
========

The Essex release uses a completely new database backend as of Essex
Milestone 4, which means your old database schema will not be compatible, and
must be undergo a data migration.


Preparing Your Essex Deployment
-------------------------------

By default, Essex is configured to use an in-memory backend (``kvs``) instead
of a SQL backend. To change this, modify your new ``etc/keystone.conf`` from
it's default value::

    [identity]
    driver = keystone.identity.backends.kvs.Identity

... to instead use a SQL driver::

    [identity]
    driver = keystone.identity.backends.sql.Identity

You may also want to configure your ``[sql]`` settings to better reflect your
environment::

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
empty list from our new database)::

    $ keystone --token ADMIN --endpoint http://127.0.0.1:35357/v2.0/ tenant-list
    +----+------+---------+
    | id | name | enabled |
    +----+------+---------+
    +----+------+---------+


Importing from Diablo
---------------------

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

    $ keystone-manage import_legacy <connection_str>

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
