:orphan:

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

===========
Setup Abfab
===========

Installing mod_moonshot
=======================

Federate Keystone (SP) and an external IdP using ABFAB (`mod_moonshot`_)

.. _`mod_moonshot`: http://www.project-moonshot.org

The links below present instructions to install mod_moonshot (aka auth_gssapi)
on some compatible Linux flavours. This module is compatible with Apache HTTPD
server v2.22.

Ubuntu 12.04 LTS:

* `Install Moonshot Libraries on Ubuntu 12.04 LTS`_
* `Install mod_moonshot on Ubuntu 12.04 LTS`_

Ubuntu 14.04 LTS:

* `Install Moonshot Libraries on Ubuntu 14.04 LTS`_
* `Install mod_moonshot on Ubuntu 14.04 LTS`_

Debian 7:

* `Install Moonshot Libraries on Debian 7`_
* `Install mod_moonshot on Debian 7`_

RedHat Enterprise Linux 6 / CentOS 6 / SE Linux 6:

* `Install Moonshot Libraries on RHEL6 / CentOS 6 / SE Linux 6`_
* `Install mod_moonshot on RHEL6 / CentOS 6 / SE Linux 6`_

.. _`Install Moonshot Libraries on Ubuntu 12.04 LTS`: https://wiki.moonshot.ja.net/display/Moonshot/Install+Moonshot+Libraries+on+Ubuntu+12.04+LTS
.. _`Install mod_moonshot on Ubuntu 12.04 LTS`: https://wiki.moonshot.ja.net/display/Moonshot/Apache+HTTPD+on+Debian+7
.. _`Install Moonshot Libraries on Ubuntu 14.04 LTS`: https://wiki.moonshot.ja.net/display/Moonshot/Install+Moonshot+Libraries+on+Ubuntu+14.04+LTS
.. _`Install mod_moonshot on Ubuntu 14.04 LTS`: https://wiki.moonshot.ja.net/display/Moonshot/Apache+HTTPD+on+Debian+7
.. _`Install Moonshot Libraries on Debian 7`: https://wiki.moonshot.ja.net/display/Moonshot/Install+Moonshot+Libraries+on+Debian+7
.. _`Install mod_moonshot on Debian 7`: https://wiki.moonshot.ja.net/display/Moonshot/Apache+HTTPD+on+Debian+7
.. _`Install Moonshot Libraries on RHEL6 / CentOS 6 / SE Linux 6`: https://wiki.moonshot.ja.net/pages/viewpage.action?pageId=2687416
.. _`Install mod_moonshot on RHEL6 / CentOS 6 / SE Linux 6`: https://wiki.moonshot.ja.net/pages/viewpage.action?pageId=4030707

Configuring mod_moonshot
========================

After installing mod_moonshot, configure it to `connect to an ABFAB IdP`_.

.. _`connect to an ABFAB IdP`: https://wiki.moonshot.ja.net/display/Moonshot/Configure+a+Linux+Server+to+Connect+to+an+RP+Proxy

Mod_moonshot also needs Shibboleth service configuration files located at
/etc/shibboleth.

On RHEL, CentOS or SE Linux distributions, shibd is installed with moonshot
libraries, so the files just need to be configured.

On Ubuntu 12.04 or 14.04, you can install mod_shib installed, and disable it.

.. code-block:: bash

  $ apt-get install mod_shib 
  $ a2dismod shib2

Or you can optionally set up the /etc/shibboleth files manually.
For instructions on how to configure Shibboleth, follow the steps on section
"Configuring shibboleth2.xml" in this `link`_.

.. _`link`: http://docs.openstack.org/developer/keystone/extensions/shibboleth.html

In the keystone Apache site file, locate the virtual host entry and add the
following entries for ABFAB:

.. code-block:: xml

  <VirtualHost *:5000>
      ...
      <LocationMatch /v3/OS-FEDERATION/identity_providers/.*?/protocols/abfab/auth>
          AuthType Negotiate
          Require valid-user
      </LocationMatch>
  </VirtualHost>

  <VirtualHost *:35357>
      ...
      <LocationMatch /v3/OS-FEDERATION/identity_providers/.*?/protocols/abfab/auth>
          AuthType Negotiate
          Require valid-user
      </LocationMatch>
  </VirtualHost>

Notes:

1. abfab may be different in your deployment.
2. Using a different wildcard instead of ".*" (eg. "Abfab.*") will make only
   IdPs prefixed with "Abfab" to authenticate using "abfab" protocol.

Once you are done, restart your Apache daemon:

.. code-block:: bash

    $ service apache2 restart
