Rally job related files
=======================

This directory contains Rally tasks and plugins that are run by OpenStack CI.

Structure
---------

* *keystone.yaml* is a task that will be run in gates against OpenStack deployed
  by DevStack.

* *plugins/* - directory where you can add Rally plugins. Almost everything in
  Rally is plugin. Benchmark context, Benchmark scenario, SLA checks, Generic
  cleanup resources, ....

* *extra/* - all files from this directory will be copied to gates, so you
  are able to use absolute path in Rally tasks.
  Files will appear in *~/.rally/extra/**


Useful links
------------

* More about Rally: https://rally.readthedocs.org/en/latest/

* Rally release notes: https://rally.readthedocs.org/en/latest/release_notes.html

* How to add rally-gates: https://rally.readthedocs.org/en/latest/gates.html

* About plugins:  https://rally.readthedocs.org/en/latest/plugins.html

* Plugin samples: https://github.com/openstack/rally/tree/master/samples/plugins
