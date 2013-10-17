..
      Copyright 2013 OpenStack, Foundation
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

=================
Extension Example
=================

Please describe here in details how to enable your extension:

1. Add the required fields and values in the ``[example]`` section
   in ``keystone.conf``.

2. Optional: add the required ``filter`` to the ``pipeline`` in ``keystone-paste.ini``

3. Optional: create the extension tables if using the provided sql backend. Example::


    ./bin/keystone-manage db_sync --extension example

4. Optional: subscribe to ``resources`` notification events
   ``Resources`` in Keystone that produce notifications are:


    - ``group``
    - ``project`` (i.e. "tenant")
    - ``role``
    - ``user``


   In order to subscribe to event notifications, the extension must provide the list of events it is interested in and their corresponding callbacks.
   In the ``routers.py`` file the following dictionary has to be created:


.. code:: python
       subscribed_events = {
          'identity.project.deleted': controllers.ExampleV3Controller.project_deleted_notification,
          'identity.project.created': controllers.ExampleV3Controller.project_created_notification
       }


   where the key represents the identity event of interest and the value is the callback.
   Events in Keystone follow this format: identity.<resource>.<operation> where the
   operations are ``created``, ``updated`` and ``deleted``.


Lastly the extension has to register the dictionary of events with the
``extension_notifier`` notification driver:


.. code:: python
       extensions_notifier.register(subscribed_events)
