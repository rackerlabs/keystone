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

=============
Caching Layer
=============

The caching layer is designed to be applied to any ``manager`` object within Keystone
via the use of `oslo_cache`_.

.. _oslo_cache: https://github.com/openstack/oslo.cache

The caching can be setup for all or some subsystems. It is recommended that each of the
managers have an independent toggle within the config file to enable caching. The easiest
method to utilize the toggle within the configuration file is to define a ``caching`` boolean
option within that manager's configuration section (e.g. ``resource``). Enable the global cache
``enabled`` option as well as the specific manager's caching enable toggle in order to cache
that subsystem.

The `oslo_cache`_ is simple and easy to adopt by any system. See the `usage guide`_ of
it. There are various cache :ref:`backends <caching_layer>` supported by it. Example use of `oslo_cache`_ in
keystone (in this example, ``resource`` is the manager):

.. code-block:: python

    from keystone.common import cache
    MEMOIZE = cache.get_memoization_decorator(group='resource')

    @MEMOIZE
    def get_domain(self, domain_id):
        ...
        return some_value

.. _usage guide: https://docs.openstack.org/oslo.cache/latest/user/usage.html

It is recommended that each of the managers to have an independent configurable time-to-live (TTL).
For consistency, it is recommended that this option be called ``cache_time`` and default to ``None``.
If the ``cache_time`` is set to ``None``, the expiration time will be set to the global default
``expiration_time`` option in the ``[cache]`` configuration section. Example for caching ``resource``
in ``/etc/keystone/keystone.conf``:

.. code-block:: ini

   [cache]
   enabled=true

   [resource]
   caching=true
   cache_time=600

:ref:`Cache invalidation <cache_invalidation>` can be done if specific cache entries are changed.


