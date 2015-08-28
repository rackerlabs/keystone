..
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

===========================
Developing Keystone Drivers
===========================

A driver, also known as a backend, is an important architectural
component of Keystone. It is an abstraction around the data access
needed by a particular subsystem. This pluggable implementation is not
only how Keystone implements its own data access, but how you can
implement your own!

Each major subsystem (that has data access needs) implements the data access
by using drivers. Some examples of Keystone's drivers:

- keystone.identity.backends.ldap:Identity
- keystone.token.providers.fernet:Provider
- keystone.contrib.federation.backends.sql:Federation

In/Out of Tree
--------------

It's best to start developing your custom driver outside of the Keystone
ecosystem. This is better for you because it gives you more freedom and
you are not bound to the strict OpenStack development rules. You can
iterate faster and take whatever shortcuts you need to get your product
out of the door.

This is also good for Keystone because it will limit the amount of drivers
that must be maintained by the team. If the team had to maintain a
driver for each NoSQL DB that deployers want to use in production there
would be less time to make Keystone itself better. Not to mention that
the team would have to start gaining expertise in potentially dozens of
new technologies.

As you'll see below there is no penalty for open sourcing your driver,
on GitHub for example, or even keeping your implementation private. We
use `Setuptools entry points`_ to load your driver from anywhere in the
Python path.

.. _Setuptools entry points: no good resource?

How To Make a Driver
--------------------

The TLDR; steps (and too long didn't write yet):

1. Determine which subsystem you would like write a driver for
2. Subclass the most current version of the driver interface
3. Implement each of the abstract methods for that driver
   a. Guess at the inputs/outputs or maybe do some debugging to figure
      it out
   b. Definitely cross your fingers!
4. Register your new driver as an entry point
5. Configure your new driver in ``keystone.conf``
6. Sit back and profit!

Driver Versioning
-----------------

In the past the driver class was named ``Driver`` and changes would
sometimes be devastating to developers that depend on our driver
contracts. To help alleviate some of the issues we are now creating
version driver classes, e.g. ``Driver11``.

We'll be supporting the current driver version for typically 1 version back.
This will give developers a full cycle to update their drivers. There
may be some cases where we have to make a breaking change and we do
reserve that right.

As new driver interface versions are added old ones will be modified to
output deprecation messages when used. Unsupported versions will just be
deleted altogether.

Removing Methods
~~~~~~~~~~~~~~~~

Newer driver interface may remove methods that are currently required.
When the method is removed it will no longer be called by Keystone. If
you rely on it being called, maybe for auditing, this will no longer
work.

There is no reason why you have to remove the method from your
implementation just because we remove it from ours.

Adding Methods
--------------

The most common API changes will be adding method to support new
features. We'll do our best to add methods in a way that is backward
compatible. The new version of the driver will define the new method as
an ``abc.abstractmethod`` that must be implemented by driver
implementations. We'll also go back to our supported drivers and add the
method, with a default implementation, when possible.

For example, given a ``thing.DriverV11`` that added a new method
``list_things_by_name()``, we'd go back to ``thing.Driver10`` and
implement that method. This is good because in many cases your driver
will just work, but there are a couple of unfortunate side effects.
First if you have already used that method name you will have to rename
your method and cut a new version. Second is that the default
implementation may cause a performance penalty due to it naive
implementation.

Updating Methods
~~~~~~~~~~~~~~~~

We will try not to update existing methods in ways that will break old
driver implementations. That means that:

* we will respect existing parameters and not just delete them. If they are
  to be removed we will respect their behavior and deprecate then in older
  versions.
* we will add new parameters as optional with backward compatible defaults.
