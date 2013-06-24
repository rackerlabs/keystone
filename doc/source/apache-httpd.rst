
..
      Copyright 2011-2012 OpenStack, LLC
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

=========================
Running Keystone in HTTPD
=========================


SSL
===

To run Keystone in HTTPD, first enable SSL support.  This is optional,  but highly recommended.

Install mod_nss according to your distribution, then apply the following patch and restart HTTPD::

    --- /etc/httpd/conf.d/nss.conf.orig	2012-03-29 12:59:06.319470425 -0400
    +++ /etc/httpd/conf.d/nss.conf	2012-03-29 12:19:38.862721465 -0400
    @@ -17,7 +17,7 @@
     # Note: Configurations that use IPv6 but not IPv4-mapped addresses need two
     #       Listen directives: "Listen [::]:8443" and "Listen 0.0.0.0:443"
     #
    -Listen 8443
    +Listen 443

     ##
     ##  SSL Global Context
    @@ -81,7 +81,7 @@
     ## SSL Virtual Host Context
     ##

    -<virtualhost _default_:8443="">
    +<virtualhost _default_:443="">

     #   General setup for the virtual host
     #DocumentRoot "/etc/httpd/htdocs"
    </virtualhost></virtualhost>

Firewall
--------

Add the following rule to IPTables in order to ensure the SSL traffic can pass your firewall::

    -A INPUT -m state --state NEW -m tcp -p tcp --dport 443 -j ACCEPT

it goes right before::

    -A INPUT -j REJECT --reject-with icmp-host-prohibited

Files
-----

Copy the file httpd/wsgi-keystone.conf to the appropriate location for your apache server, most likely::

    /etc/httpd/conf.d/wsgi-keystone.conf

Create the directory ``/var/www/cgi-bin/keystone/``. You can either hardlink or softlink the files ``main`` and ``admin`` to the file ``keystone.py`` in this directory.  For a distribution appropriate place, it should probably be copied to::

    /usr/share/openstack/keystone/httpd/keystone.py

Keystone's primary configuration file (``etc/keystone.conf``) and the PasteDeploy
configuration file (``etc/keystone-paste.ini``) must be readable to HTTPD in
one of the default locations described in :doc:`configuration`.

SELinux
-------

If you are running with SELinux enabled (and you should be) make sure that the file has the appropriate SELinux context to access the linked file.  If you have the file in /var/www/cgi-bin,  you can do this by running::

    sudo restorecon /var/www/cgi-bin

Putting it somewhere else requires you set up your SELinux policy accordingly.

Keystone Configuration
----------------------

Make sure you use the ``SQL`` driver for ``tokens``, otherwise the tokens will not be shared between the processes of the Apache HTTPD server.  To do that, in ``/etc/keystone/keystone.conf`` make sure you have set::

    [token]
    driver = keystone.token.backends.sql.Token

Authentication File Setup
-------------------------

Create a new directory ``/var/www/stack/auth/`` and make sure HTTPD has access to the directory::

    $ sudo mkdir /var/www/stack/auth
    $ sudo chmod 755 /var/www/stack/auth

Create an .htpasswd file in ``/var/www/stack/auth/`` with at least one user.
The user will need to have the same username as an OpenStack user that has
sufficient permissions to do what is needed in OpenStack after HTTPD
authentication occurs. Replace admin with whichever user you plan to use::

    $ sudo htpasswd -c /var/www/stack/auth/.htpasswd admin
    New password:
    Re-type new password:

Ensure the .htpasswd file has permission so HTTPD can access it::

    $ sudo chmod 755 /var/www/stack/auth/.htpasswd

Verify that the ``/opt/stack/keystone/httpd/keystone.py`` file and symlinks
to keystone.py exist

Create a ``/etc/httpd/conf.d/keystone.conf`` file with these contents. This
tells Apache where to find the Keystone admin and main scripts, what ports to
use them for, and what file to use for authentication::

 Listen 35357

  <VirtualHost *:35357>
    WSGIScriptAlias /  [Keystone Install Root]/httpd/admin
    <Location /v2.0/tokens>
      <Limit POST>
        AuthType Basic
      </Limit>
    </Location>
  </VirtualHost>

 Listen 5000

 <VirtualHost *:5000>
   WSGIScriptAlias /  [Keystone Install Root]/httpd/main
   <Location /v2.0/tokens>
     AuthType Basic
     AuthName OpenStack
     AuthUserFile /var/www/stack/auth/.htpasswd
     Require valid-user
   </Location>
 </VirtualHost>

Ensure the user running Apache will have access to the keystone.conf file::

    $ chmod 0744 /etc/keystone/keystone.conf

Make sure MySQL is running and verify the Keystone standalone process is
still down. Restart Apache to pick up all changes::

    $ sudo service httpd restart

If no configuration errors get thrown by the Apache restart, Keystone should
now be accessible.

Verification Authentication Works
---------------------------------

A quick way to verify the authentication is working is to use curl commands from
the command line.  Note that the Keystone API commands can't be used, as they
don't set a username and password in the HTTP header.  Apache verifies the
username and password passed in the header using the REMOTE_USER variable for
authentication.

Example of getting a new token with authentication of the username and password
in the .htpasswd file::

 $ curl -i --user [Username for File Authentication]:[Password for File Authentication] -H "Content-Type: application/json" -d '{"auth": {}}' http://localhost:35357/v2.0/tokens

Response::

 HTTP/1.1 200 OK
 Date: Mon, 04 Mar 2013 22:49:49 GMT
 Server: Apache/2.2.22 (Ubuntu)
 Vary: X-Auth-Token
 Content-Length: 1133
 Content-Type: application/json

 {"access": {"token": {"issued_at": "2013-03-04T22:49:49.463120", "expires": "2013-03-05T22:49:49Z", "id": "MIICbgYJKoZIhvcNAQcCoIICXzCCAlsCAQExCTAHBgUrDgMCGjCCAUcGCSqGSIb3DQEHAaCCATgEggE0eyJhY2Nlc3MiOiB7InRva2VuIjogeyJpc3N1ZWRfYXQiOiAiMjAxMy0wMy0wNFQyMjo0OTo0OS40NjMxMjAiLCAiZXhwaXJlcyI6ICIyMDEzLTAzLTA1VDIyOjQ5OjQ5WiIsICJpZCI6ICJwbGFjZWhvbGRlciJ9LCAic2VydmljZUNhdGFsb2ciOiBbXSwgInVzZXIiOiB7InVzZXJuYW1lIjogImFkbWluIiwgInJvbGVzX2xpbmtzIjogW10sICJpZCI6ICI0MjRmOTc5NTgzODQ0MjU4YWMwMDgyNWU2MjE0MDE1NCIsICJyb2xlcyI6IFtdLCAibmFtZSI6ICJhZG1pbiJ9LCAibWV0YWRhdGEiOiB7ImlzX2FkbWluIjogMCwgInJvbGVzIjogW119fX0xgf8wgfwCAQEwXDBXMQswCQYDVQQGEwJVUzEOMAwGA1UECBMFVW5zZXQxDjAMBgNVBAcTBVVuc2V0MQ4wDAYDVQQKEwVVbnNldDEYMBYGA1UEAxMPd3d3LmV4YW1wbGUuY29tAgEBMAcGBSsOAwIaMA0GCSqGSIb3DQEBAQUABIGAnTE7sARodxe3Rm-eD-9HP9E1KgusnEZSaLO-Fpz5+Nfx68WZknB61AQDllZ3WG4nPzttpxEQ28fl6qZXuFHnb7PBHuTSI1-xVx5TIAoJaW7EO6-0kwsqn0lRclY6NoHsYUPOdJn7K41Rf8XoXovQVYd5lsxZPgrCkZHomC0Vc10="}, "serviceCatalog": [], "user": {"username": "admin", "roles_links": [], "id": "424f979583844258ac00825e62140154", "roles": [], "name": "admin"}, "metadata": {"is_admin": 0, "roles": []}}}

Note: Depending on your setup, the token ID value in the response may be a different format/length.
