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

====================
Configure the OAuth1
====================

To enable the OAuth1:

1. Add the oauth1 extension driver to the ``[oauth1]`` section in ``keystone.conf``. For example::

    [oauth1]
    driver = sql

2. Add the ``oauth1`` authentication method to the ``[auth]`` section in ``keystone.conf``::

    [auth]
    methods = external,password,token,oauth1

3. Optionally, if deploying under an HTTPD server (i.e. Apache), set the
   `WSGIPassAuthorization` to allow the OAuth Authorization headers to
   pass through `mod_wsgi`. For example, add the following to the Keystone
   virtual host file::

    WSGIPassAuthorization On
