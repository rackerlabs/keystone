..
      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

      http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

=============================
Configure the Endpoint Filter
=============================

1. Add the endpoint filter catalog driver to the ``[catalog]`` section
   in ``keystone.conf``. For example::

    [catalog]
    driver = catalog_sql


2. Change ``return_all_endpoints_if_no_filter`` the ``[endpoint_filter]`` section
   in ``keystone.conf`` to return an empty catalog if no associations are made. For example::

    [endpoint_filter]
    return_all_endpoints_if_no_filter = False
