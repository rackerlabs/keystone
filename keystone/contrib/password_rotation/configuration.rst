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

===========================
Password Rotation Extension
===========================

To enable the``OS-PW-ROTATE`` extension:

1. Add the required ``filter`` to the ``pipeline`` in ``keystone-paste.ini``::

    [filter:password_rotation_extension]
    paste.filter_factory = keystone.contrib.password_rotation.routers:ExtensionRouter.factory

    [pipeline:api_v3]
    pipeline = [...existing pipeline...] password_rotation_extension service_v3

2. Optional: Set the ``blah`` config value in your ``keystone.conf``. This
   will allow you to control how long rotated password and considered valid.
