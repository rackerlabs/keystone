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

===================
Setting up Keystone
===================

.. _dev-environment:

Setting up the Developer Environment
====================================

This section describes getting the source from keystone's `Git Repository`_
and setting the environment up for development purposes.

To install keystone from packaging, refer instead to OpenStack's `User
Documentation`_.

.. _`Git Repository`: https://git.openstack.org/cgit/openstack/keystone
.. _`User Documentation`: https://docs.openstack.org/

Prerequisites
-------------

This document assumes you are using an Ubuntu, Fedora, or openSUSE platform and
that you have the following tools pre-installed on your system:

- Python_ 2.7 and 3.5, as the programming language;
- git_, as the version control tool;

**Reminder**: If you are successfully using a different platform, or a
different version of the above, please document your configuration here!

.. _git: http://git-scm.com/
.. _Python: http://www.python.org/

Getting the latest code
-----------------------

Make a clone of the code from our git repository and enter the directory:

.. code-block:: bash

    $ git clone https://git.openstack.org/openstack/keystone.git
    $ cd keystone

Development environment
-----------------------

For setting up the Python development environment and running `tox` testing
environments, please refer to the `Project Team Guide: Python Project Guide`_,
the OpenStack guide on wide standard practices around the use of Python.

That documentation will guide you to configure your development environment
and run keystone tests using `tox`, which uses virtualenv_ to isolate the Python
environment. It is recommended that you install Keystone into a virtualenv.
After running `tox`, notice the existence of a `.tox` directory.

.. _`Project Team Guide: Python Project Guide`: https://docs.openstack.org/project-team-guide/project-setup/python.html
.. _virtualenv: http://www.virtualenv.org/

Verifying keystone is set up
----------------------------

Once set up, you should be able to invoke Python and import the libraries:

.. code-block:: bash

    $ .tox/py27/bin/python -c "import keystone"

If you can import keystone without a traceback, you should be ready to move on
to the next sections.

Database setup
--------------

The script ``tools/test-setup.sh`` sets up databases as used by the
unit tests.

Configuring Keystone with a sample file
=======================================

Keystone requires a configuration file. Keystone's sample configuration file
``etc/keystone.conf.sample`` is automatically generated based upon all of the
options available within Keystone. These options are sourced from the many
files around Keystone as well as some external libraries.

The sample configuration file will be updated as the end of the development
cycle approaches. Developers should *NOT* generate the config file and propose
it as part of their patches, this will cause unnecessary conflicts.
You can generate one locally using the following command:

.. code-block:: bash

    $ tox -e genconfig

The tox command will place an updated sample config in ``etc/keystone.conf.sample``.
The defaults are enough to get you going, but you can make any changes if
needed.

If there is a new external library (e.g. ``oslo.messaging``) that utilizes the
``oslo.config`` package for configuration, it can be added to the list of libraries
found in ``config-generator/keystone.conf``.

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
