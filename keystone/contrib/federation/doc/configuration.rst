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
Enablig Federation Extension
=================

To enable the federation extension:

  1. add the federation extension catalog driver to the ``[federation]`` section
     in ``keystone.conf``. example::

      [federation]
      driver = keystone.contrib.federation.backends.sql.IdentityProvider

  2. add the ``federation_extension`` filter to the ``api_v3`` pipeline in
     ``keystone-paste.ini``.

      [pipeline:api_v3]
      pipeline = access_log sizelimit url_normalize token_auth
      admin_token_auth xml_body json_body ec2_extension
      s3_extension federation_extension service_v3

3. create the federation extension tables if using the provided sql backend.
    ./bin/keystone-manage db_sync --extension federation
