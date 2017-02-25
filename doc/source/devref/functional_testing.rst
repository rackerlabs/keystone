..
      Copyright 2017 Massachusetts Open Cloud
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

==================
Functional Testing
==================

Functional tests are currently run in two gates using the tempest plugin
available under ``keystone_tempest_plugin``.

- gate1 - is voting and exposes both the v2 and v3 endpoint.
- gate2 - is non-voting and exposes only the v3 endpoint, but additionally,
  it runs federation tests.

Devstack Plugin
===============

To help with automating an appropriate environment on which to run functional
tests, keystone provides a Devstack plugin.

As of right now, the plugin only supports setting up and environment with
federation and keystone as a service provider, but more features are to
come.

To enable the plugin add

    enable_plugin keystone git://git.openstack.org/openstack/keystone.git

Keystone as an SP
-----------------
Document the exposed fields via settings.
