keystone-status
~~~~~~~~~~~~~~~

-----------------------
Keystone Status Utility
-----------------------

:Author: openstack@lists.openstack.org
:Date: 2018-10-15
:Copyright: OpenStack Foundation
:Version: 14.0.0
:Manual section: 1
:Manual group: cloud computing

SYNOPSIS
========

  keystone-status [options]

DESCRIPTION
===========

``keystone-status`` is a command line tool that helps operators upgrade their
deployment.

USAGE
=====

    ``keystone-status [options] action [additional args]``

.. include:: upgrade.rst

OPTIONS
=======

  -h, --help            show this help message and exit
  --config-dir DIR      Path to a config directory to pull \*.conf files from.
                        This file set is sorted, so as to provide a
                        predictable parse order if individual options are
                        over-ridden. The set is parsed after the file(s)
                        specified via previous --config-file, arguments hence
                        over-ridden options in the directory take precedence.
  --config-file PATH    Path to a config file to use. Multiple config files
                        can be specified, with values in later files taking
                        precedence. Defaults to None.

FILES
=====

None

SEE ALSO
========

* `OpenStack Keystone <https://docs.openstack.org/keystone/latest>`__

SOURCE
======

* Keystone is sourced in Gerrit git `Keystone <https://git.openstack.org/cgit/openstack/keystone>`__
* Keystone bugs are managed at Launchpad `Keystone <https://bugs.launchpad.net/keystone>`__
