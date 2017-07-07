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

====================================
Setting up a Development Environment
====================================

This document describes getting the source from keystone's `Git Repository`_
and setting the environment up for development purposes.

To install keystone from packaging, refer instead to OpenStack's `User
Documentation`_.

.. _`Git Repository`: https://git.openstack.org/cgit/openstack/keystone
.. _`User Documentation`: https://docs.openstack.org/

Prerequisites
=============

This document assumes you are using an Ubuntu, Fedora, or openSUSE platform and
that you have the following tools pre-installed on your system:

- Python_ 2.7 and 3.5, as the programming language;
- git_, as the version control tool;

**Reminder**: If you are successfully using a different platform, or a
different version of the above, please document your configuration here!

.. _git: http://git-scm.com/
.. _Python: http://www.python.org/

Installing from source
======================

Clone the git repository and install it using ``pip``:

.. code-block:: bash

    $ git clone https://git.openstack.org/openstack/keystone.git
    $ cd keystone
    $ pip install -e .

.. NOTE::

    This step is guaranteed to fail if you do not have the proper binary
    dependencies already installed on your development system. Maintaining a
    list of platform-specific dependencies is outside the scope of this
    documentation, but is within scope of DEVSTACK_.

.. _DEVSTACK: https://docs.openstack.org/developer/devstack/

Development environment
=======================

For setting up the Python development environment and running `tox` testing
environments, please refer to the `Project Team Guide: Python Project Guide`_,
the OpenStack guide on wide standard practices around the use of Python.

That documentation will guide you to configure your development environment
and run keystone tests using `tox`, which uses virtualenv_ to isolate the Python
environment. After running it, notice the existence of a `.tox` directory.

.. _`Project Team Guide: Python Project Guide`: https://docs.openstack.org/project-team-guide/project-setup/python.html
.. _virtualenv: http://www.virtualenv.org/

Deploying configuration files
=============================

You should have all the pieces you need to run Keystone installed on your
system. The following commands should be available on the command-line path:

* ``keystone`` the Keystone client, used to interact with Keystone
* ``keystone-manage`` used to bootstrap Keystone data

You will find sample configuration files in ``etc/``:

* ``keystone.conf``
* ``keystone-paste.ini``
* ``logging.conf``
* ``policy.json``
* ``default_catalog.templates``

From here, refer to :doc:`../configuration` to choose which backend drivers to
enable and use. Once configured, you should be able to run Keystone by issuing
the command:

Verifying keystone is set up
============================

Once set up, you should be able to invoke Python and import the libraries:

.. code-block:: bash

    $ .tox/py27/bin/python -c "import keystone"

If you can import keystone without a traceback, you should be ready to move on
to :doc:`development_best_practices`.

You can run keystone using a host of wsgi implementations or web servers. The
following uses ``uwsgi``:

.. code-block:: bash

    $ uwsgi --http 127.0.0.1:35357 --wsgi-file $(which keystone-wsgi-admin)

Database setup
==============

The script ``tools/test-setup.sh`` sets up databases as used by the
unit tests.

Bootstrapping a test deployment
===============================

You can use the ``keystone-manage bootstrap`` command to pre-populate the
database with necessary data.
