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

===============================
Command Line Interface Examples
===============================

--------
Projects
--------

``project create``
------------------

positional arguments::

  <project-name>                        New project name

optional arguments::

  --description <project-description>   New project description
  --enable                              Enable project (default)
  --disable                             Disable project

example:

.. code-block:: bash

    $ openstack project create demo

``project delete``
------------------

positional arguments::

  <project>   Project to delete (name or ID)

example:

.. code-block:: bash

    $ openstack project delete demo

-----
Users
-----

``user create``
---------------

positional arguments::

  <user-name>                  New user name

optional arguments::

  --password <user-password>   New user password
  --password-prompt            Prompt interactively for password
  --email <user-email>         New user email address
  --project <project>          Set default project (name or ID)
  --enable                     Enable user (default)
  --disable                    Disable user


example:

.. code-block:: bash

    $ openstack user create heat-user \
    --password secrete \
    --project demo \
    --email admin@example.com

``user delete``
---------------

positional arguments::

  <user>   User to delete (name or ID)

example:

.. code-block:: bash

    $ openstack user delete heat-user

``user list``
-------------

optional arguments::

  --project <project>   Filter users by project (name or ID)
  --long                List additional fields in output

example:

.. code-block:: bash

    $ openstack user list

``user set``
------------

positional arguments::

  <user>                       User to change (name or ID)

optional arguments::

  --name <new-user-name>       New user name
  --password <user-password>   New user password
  --password-prompt            Prompt interactively for password
  --email <user-email>         New user email address
  --project <project>          New default project (name or ID)
  --enable                     Enable user (default)
  --disable                    Disable user


example:

.. code-block:: bash

    $ openstack user set heat-user --email newemail@example.com

-----
Roles
-----

``role create``
---------------

positional arguments::

  <role-name>           New role name

example:

.. code-block:: bash

    $ openstack role create demo

``role delete``
---------------

positional arguments::

  <role>      Name or ID of role to delete

example:

.. code-block:: bash

    $ openstack role delete demo

``role list``
-------------

example:

.. code-block:: bash

    $ openstack role list

``role show``
-------------

positional arguments::

  <role>                Name or ID of role to display

example:

.. code-block:: bash

    $ openstack role show demo


``role add``
------------

positional arguments::

  <role>                Role name or ID to add to user

optional arguments::

  --project <project>   Include project (name or ID)
  --user <user>         Name or ID of user to include


example:

.. code-block:: bash

    $ openstack user role add  demo --user heat-user --project heat

``role remove``
---------------

positional arguments::

  <role>               Role name or ID to remove from user

optional arguments::

  --project <project>  Project to include (name or ID)
  --user <user>        Name or ID of user


example:

.. code-block:: bash

    $ openstack user role remove  demo --user heat-user --project heat

--------
Services
--------

``service create``
------------------

positional arguments::

  <service-name>   New service name

optional arguments::

  --type <service-type>   New service type (compute, image, identity, volume, etc)
  --description <service-description>   New service description

example:

.. code-block:: bash

  $ openstack service create nova --type compute --description "Nova Compute Service"

``service list``
----------------

optional arguments::

  --long   List additional fields in output

example:

.. code-block:: bash

  $ openstack service list

``service show``
----------------

positional arguments::

  <service>   Service to display (type, name or ID)

example:

.. code-block:: bash

  $ openstack service show nova

``service delete``
------------------

positional arguments::

  <service>   Service to delete (name or ID)

example:

.. code-block:: bash

  $ openstack service delete nova
