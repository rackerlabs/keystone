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

=============================================
Setting up a Keystone development environment
=============================================

This document describes getting the source from Keystone's `Git repository`_
for development purposes.

To install Keystone from packaging, refer instead to Keystone's `User
Documentation`_.

.. _`Git Repository`: http://git.openstack.org/cgit/openstack/keystone
.. _`User Documentation`: http://docs.openstack.org/

Installing system dependencies
==============================
This document assumes you are using Ubuntu, Fedora or openSUSE (SLE)

Ubuntu 14.04:

.. code-block:: bash

    $ sudo apt-get install python-dev python3-dev libxml2-dev libxslt1-dev \
        libsasl2-dev libsqlite3-dev libssl-dev libldap2-dev libffi-dev


Fedora 19+:

.. code-block:: bash

    $ sudo yum install python-lxml python-greenlet-devel python-ldap sqlite-devel \
        openldap-devel python-devel libxslt-devel openssl-devel libffi-devel

openSUSE 13.2 (SLE 12):

.. code-block:: bash

    $ sudo zypper install libxslt-devel openldap2-devel libopenssl-devel python-devel \
        python-greenlet-devel python-ldap python-lxml python-pysqlite sqlite3-devel

Getting the latest code
=======================

Make a clone of the code from our `Git repository`:

.. code-block:: bash

    $ git clone https://git.openstack.org/openstack/keystone.git

When that is complete, you can:

.. code-block:: bash

    $ cd keystone

Setting up a virtual environment
================================

To install dependencies from PyPi_ to virtualenv, install the Python tool pip_.

.. _PyPi: http://pypi.python.org/
.. _pip: http://pypi.python.org/pypi/pip

Once pip has been installed, install ``tox``

.. code-block:: bash

    $ pip install tox

To install dependencies within virtualenv, run:

.. code-block:: bash

    $ tox -e py27 --notest

To activate virtual environment, run:

.. code-block:: bash

    $ source .tox/py27/bin/activate

The virtual environment can be disabled using the command:

.. code-block:: bash

    $ deactivate

Verifying Keystone is set up
============================

Once set up within a virtualenv, you should be able to invoke Python and
import the libraries. Don't forget to activate it:

.. code-block:: bash

    $ source .tox/py27/bin/activate

You should be able to `import keystone` using Python without issue:

.. code-block:: bash

    $ python -c "import keystone"

If you can import Keystone without a traceback, you should be ready to move on
to :doc:`../developing`.
