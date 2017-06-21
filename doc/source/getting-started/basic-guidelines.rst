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

================
Basic Guidelines
================

Setting up Keystone
===================

Get your development environment set up according to
:doc:`../devref/development_environment`. It is recommended that you install
Keystone into a virtualenv.


Configuring Keystone
====================

Keystone requires a configuration file. There is a sample configuration file
that can be used to get started:

.. code-block:: bash

    $ cp etc/keystone.conf.sample etc/keystone.conf

The defaults are enough to get you going, but you can make any changes if
needed.


Running Keystone
================

To run the Keystone Admin and API server instances, use:

.. code-block:: bash

    $ uwsgi --http 127.0.0.1:35357 --wsgi-file $(which keystone-wsgi-admin)

This runs Keystone with the configuration the etc/ directory of the project.
See :doc:`../configuration` for details on how Keystone is configured. By default,
Keystone is configured with SQL backends.


Initializing Keystone
=====================

Before using keystone, it is necessary to create the database tables and ensures
the database schemas are up to date, perform the following:

.. code-block:: bash

    $ keystone-manage db_sync

If the above commands result in a ``KeyError``, or they fail on a
``.pyc`` file with the message, ``You can only have one Python script per
version``, then it is possible that there are out-of-date compiled Python
bytecode files in the Keystone directory tree that are causing problems. This
can occur if you have previously installed and ran older versions of Keystone.
These out-of-date files can be easily removed by running a command like the
following from the Keystone root project directory:

.. code-block:: bash

    $ find . -name "*.pyc" -delete

Initial Sample Data
-------------------

There is an included script which is helpful in setting up some initial sample
data for use with keystone:

.. code-block:: bash

    $ ADMIN_PASSWORD=s3cr3t tools/sample_data.sh

Once run, you can see the sample data that has been created by using the
`python-openstackclient`_ command-line interface:

.. code-block:: bash

    $ export OS_USERNAME=admin
    $ export OS_PASSWORD=s3cr3t
    $ export OS_PROJECT_NAME=admin
    $ export OS_USER_DOMAIN_ID=default
    $ export OS_PROJECT_DOMAIN_ID=default
    $ export OS_IDENTITY_API_VERSION=3
    $ export OS_AUTH_URL=http://localhost:5000/v3
    $ openstack user list

The `python-openstackclient`_ can be installed using the following:

.. code-block:: bash

    $ pip install python-openstackclient

Interacting with Keystone
=========================

You can also interact with keystone through its REST API. There is a Python
keystone client library `python-keystoneclient`_ which interacts exclusively
through the REST API, and a command-line interface `python-openstackclient`_
command-line interface.

.. _`python-keystoneclient`: https://git.openstack.org/cgit/openstack/python-keystoneclient
.. _`python-openstackclient`: https://git.openstack.org/cgit/openstack/python-openstackclient
