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
Setting up a keystone development environment
=============================================

This document describes getting the source from keystone's `Git Repository`_
and setting the environment up for development purposes.

To install keystone from packaging, refer instead to keystone's `User
Documentation`_.

.. _`Git Repository`: http://git.openstack.org/cgit/openstack/keystone
.. _`User Documentation`: http://docs.openstack.org/

Prerequisites
=============

This document assumes you are using an Ubuntu, Fedora or openSUSE platform and
that you have the following tools pre-installed on your system:

- Python_ 2.7 and 3.4, as the programming language;
- git_, as the version control tool;
- msgfmt_, part of the gettext package, as checker for translation files.

**Reminder**: If you are successfully using a different platform, or a
different version of the above, please document your configuration here!

.. _Python: http://www.python.org/
.. _git: http://git-scm.com/
.. _msgfmt: http://www.gnu.org/software/gettext/manual/gettext.html#msgfmt-Invocation

Getting the latest code
=======================

Make a clone of the code from our `Git Repository`:

.. code-block:: bash

    $ git clone https://git.openstack.org/openstack/keystone.git

When that is complete, you can:

.. code-block:: bash

    $ cd keystone

Keystone dependencies
=====================

Keystone maintains two lists of dependencies::

    requirements.txt
    test-requirements.txt

The first is the list of dependencies needed for running keystone, the second
list includes dependencies used for active development and testing of keystone
itself. These dependencies can be installed from PyPI_ using the Python tool
pip_.

.. _pip: http://pip.readthedocs.org/en/stable/installing/
.. _PyPI: http://pypi.python.org/

PyPI packages and virtualenv
----------------------------

virtualenv_ limits the Python environment to just what you are installing as
dependencies, thus it is useful to keep a clean working environment.

The test automation tool, tox_, will use a virtual environment to install
test dependencies when running testing environments.

If you want to run a keystone server or simply run the tests manually without
using the provided `tox` environments, we recommend establishing a `virtualenv`
before installing dependencies from the requirement files:

.. code-block:: bash

    # Install the dependencies for running keystone
    $ pip install -r requirements.txt

    # Install the dependencies for developing, testing, and running keystone
    $ pip install -r test-requirements.txt

    # Use pip to link keystone into Python's site-packages
    $ pip install -e .

.. _virtualenv: http://www.virtualenv.org/

Python and testing environments
===============================

For setting up the Python development environment and running tox_ testing
environments, please refer to the `Python infra documentation`_ on OpenStack
wide standard practices around the use of Python.

That documentation will guide you to configure your development environment
and run keystone tests using `tox`, which will use pip_ to install keystone
test dependencies listed in `test-requirements.txt`.

However, your system *may* need additional dependencies that `pip` cannot
satisfy. These dependencies should be installed accordingly your platform.

Ubuntu 14.04:

.. code-block:: bash

    $ sudo apt-get install python-dev python3-dev libxml2-dev libxslt1-dev \
        libsasl2-dev libsqlite3-dev libssl-dev libldap2-dev libffi-dev

Fedora 19+:

.. code-block:: bash

    $ sudo yum install sqlite-devel openldap-devel python-devel libxslt-devel
        openssl-devel libffi-devel

openSUSE 13.2:

.. code-block:: bash

    $ sudo zypper install libxslt-devel openldap2-devel libopenssl-devel \
        python-devel sqlite3-devel

.. _`Python infra documentation`: http://docs.openstack.org/infra/manual/python.html
.. _tox: https://tox.readthedocs.org/en/latest/

Verifying keystone is set up
============================

Once set up, you should be able to invoke Python and import the libraries. If
you are using a virtual environment, you need to make sure to use the Python
available within it; hence you need to activate it prior to calling the
interpreter, or use it directly.

If using `tox`, you should be able to import keystone with:

.. code-block:: bash

    $ .tox/py27/bin/python -c "import keystone"

If you can import keystone without a traceback, you should be ready to move on
to :doc:`../developing`.
