==========================
Tempest tests for keystone
==========================

This directory contains Tempest tests to cover the keystone project alongside
a plugin to automatically load these tests into tempest.

For further information about tempest plugins, see:
http://docs.openstack.org/developer/tempest/plugin.html#using-plugins

In order to run all the tests from this plugin, install keystone into your
environment and run (in tempest)::

    $ tox -e all-plugin -- keystone

It is also possible to specify the tests to be run, for example::

    $ tox -e all-plugin --
      keystone_tempest_plugin.tests.api.identity.admin.v3

To run all tempest plugins tests including the keystone ones, run::

    $ tox -e all-plugin

