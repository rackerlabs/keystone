..
      Copyright 2014 OpenStack, Foundation
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

=======================================
Configure the Federation authentication
=======================================

To configure federation:

1. Make sure the federation driver in the ``[federation]`` section in
   ``keystone.conf`` is set (it should be by default). For example::

       [federation]
       driver = keystone.contrib.federation.backends.sql.Federation

2. Add the ``saml2`` and/or ``oidc`` authentication methods to the ``[auth]``
   section in ``keystone.conf``::

       [auth]
       methods = external,password,token,saml2,oidc
       saml2 = keystone.auth.plugins.mapped.Mapped
       oidc = keystone.auth.plugins.mapped.Mapped

3. Add the ``federation_extension`` middleware to the ``api_v3`` pipeline in
   ``keystone-paste.ini``. This must be added after ``json_body`` and before
   the last entry in the pipeline. For example::

       [pipeline:api_v3]
       pipeline = sizelimit url_normalize build_auth_context token_auth admin_token_auth json_body ec2_extension_v3 s3_extension simple_cert_extension revoke_extension federation_extension service_v3


============================
Keystone2Keystone Federation
============================

For keystone acting as an Identity Provider it is required to manually install
``xmlsec1`` binary.

.. code-block:: bash

        $ apt-get install xmlsec1
