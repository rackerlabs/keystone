..
      Copyright 2011-2013 OpenStack, Foundation
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

==========================
Enabling Mapping Extension
==========================

To enable the mapping extension:

1. add the mapping extension catalog driver to the ``[mapping]`` section
   in ``keystone.conf``. example::

    [mapping]
    driver = keystone.contrib.mapping.backends.sql.Mapping

2. add the ``mapping_extension`` filter to the ``api_v3`` pipeline in
   ``keystone-paste.ini``. example::

    [pipeline:api_v3]
    pipeline = access_log sizelimit url_normalize token_auth admin_token_auth xml_body json_body ec2_extension s3_extension mapping_extension service_v3

3. create the mapping extension tables if using the provided sql backend. example::
    ./bin/keystone-manage db_sync --extension mapping
