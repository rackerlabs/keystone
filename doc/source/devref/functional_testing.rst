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

Functional tests exercises the functionality of software based on its
specification. They treat the software as a black box, and only examine
that the output received matches the expectation based on the input given
to the software. In keystone's case the specification is the API, and
functional tests perform API calls to a live keystone server, comparing
the received response output to the expected one.

This is different from "functional-like" tests that live in ``keystone/tests/unit/test_v3_*.py``. These tests exercise specific
components of keystone, ex. identity drivers, but not the API.

Functional tests are written as part of the tempest plugin which lives as
part of the code tree under ``keystone_tempest_plugin``.

Keystone Gates
==============

These are currently keystone's gates. All gates that have a "-nv"
suffix to them are considered non-voting and will not affect the
overall result of the check.

Tempest
-------
- gate-tempest-dsvm-neutron-full-ubuntu-xenial
- gate-grenade-dsvm-neutron-ubuntu-xenial
- gate-tempest-dsvm-py35-ubuntu-xenial
- gate-tempest-dsvm-keystone-uwsgi-full-ubuntu-xenial-nv
- gate-tempest-dsvm-neutron-identity-v3-only-full-ubuntu-xenial-nv

These gates run the entire tempest suite, which additionally to
keystone, also tests the other main services like nova and cinder.

# TODO(knikolla): Difference between neutron-full-ubuntu and neutron-ubuntu

Keystoneclient
--------------
- gate-keystoneclient-dsvm-functional-ubuntu-xenial-nv

This gate runs the ``python-keystoneclient`` functional tests with a
live keystone server.

# TODO(knikolla): Add link to python-keystoneclient functional testing.

Keystone plugin
---------------
- gate-keystone-dsvm-functional-ubuntu-xenial
- gate-keystone-dsvm-functional-v3-only-ubuntu-xenial-nv
- gate-keystone-dsvm-py35-functional-v3-only-ubuntu-xenial-nv

These gates only run the tests in ``keystone_tempest_plugin`` instead of the
entire tempest suite.

In addition, ``gate-keystone-dsvm-functional-v3-only-ubuntu-xenial-nv`` and
``gate-keystone-dsvm-py35-functional-v3-only-ubuntu-xenial-nv`` run the
Devstack plugin described below to

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
