===========================================
Using external authentication with Keystone
===========================================

When Keystone is executed in :doc:`HTTPD <apache-httpd>` it is possible to
use external authentication methods different from the authentication
provided by the identity store backend. For example, this makes possible to
use a SQL identity backend together with X.509 authentication, Kerberos, etc.
instead of using the username/password combination.

Using HTTPD authentication
==========================

Webservers like Apache HTTP support many methods of authentication. Keystone can
profit from this feature and let the authentication be done in the webserver,
that will pass down the authenticated user to Keystone using the ``REMOTE_USER``
environment variable. This user must exist in advance in the identity backend
so as to get a token from the controller.

To use this method, Keystone should be running on :doc:`HTTPD <apache-httpd>`.

X.509 example
-------------

The following snippet for the Apache conf will authenticate the user based on
a valid X.509 certificate from a known CA::

    <VirtualHost _default_:5000>
        SSLEngine on
        SSLCertificateFile    /etc/ssl/certs/ssl.cert
        SSLCertificateKeyFile /etc/ssl/private/ssl.key

        SSLCACertificatePath /etc/ssl/allowed_cas
        SSLCARevocationPath  /etc/ssl/allowed_cas
        SSLUserName          SSL_CLIENT_S_DN_CN
        SSLVerifyClient      require
        SSLVerifyDepth       10

        (...)
    </VirtualHost>

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

Developing a WSGI middleware for authentication
===============================================

In addition to the method described above, it is possible to implement other
custom authentication mechanisms using the ``REMOTE_USER`` WSGI environment
variable.

.. ATTENTION::
    Please note that even if it is possible to develop a custom authentication
    module, it is preferable to use the modules in the HTTPD server. Such
    authentication modules in webservers like Apache have normally undergone
    years of development and use in production systems and are actively maintained
    upstream. Developing a custom authentication module that implements the same
    authentication as an existing Apache module likely introduces a higher
    security risk.

If you find you must implement a custom authentication mechanism, you will need
to develop a custom WSGI middleware pipeline component. This middleware should
set the environment variable ``REMOTE_USER`` to the authenticated username.
Keystone then will assume that the user has been already authenticated upstream
and will not try to authenticate it. However, as with HTTPD authentication, the
user must exist in advance in the identity backend so that a proper token can
be issued.

Your code should set the ``REMOTE_USER`` if the user is properly authenticated,
following the semantics below::

    from keystone.common import wsgi

    class MyMiddlewareAuth(wsgi.Middleware):
        def __init__(self, *args, **kwargs):
            super(MyMiddlewareAuth, self).__init__(*args, **kwargs)

        def process_request(self, request):
            if request.environ.get('REMOTE_USER', None) is not None:
                # Assume that it is authenticated upstream
                return self.application

            if not self.is_auth_applicable(request):
                # Not applicable
                return self.application

            username = self.do_auth(request):
            if username is not None:
                # User is authenticated
                request.environ['REMOTE_USER'] = username
            else:
                # User is not authenticated, render exception
                raise exception.Unauthorized("Invalid user")


Pipeline configuration
----------------------

Once you have your WSGI middleware component developed you have to add it to
your pipeline. The first step is to add the middleware to your configuration file.
Assuming that your middleware module is ``keystone.middleware.MyMiddlewareAuth``,
you can configure it in your ``keystone-paste.ini`` as::

    [filter:my_auth]
    paste.filter_factory = keystone.middleware.MyMiddlewareAuth.factory

The second step is to add your middleware to the pipeline. The exact place where
you should place it will depend on your code (i.e. if you need for example that
the request body is converted from JSON before perform the authentication you
should place it after the ``json_body`` filter) but it should be set before the
``public_service`` (for the ``public_api`` pipeline) or ``admin_service`` (for
the ``admin_api`` pipeline), since they consume authentication.

For example, if the original pipeline looks like this::

    [pipeline:public_api]
    pipeline = stats_monitoring url_normalize token_auth admin_token_auth xml_body json_body debug ec2_extension user_crud_extension public_service

Your modified pipeline might then look like this::

    [pipeline:public_api]
    pipeline = stats_monitoring url_normalize token_auth admin_token_auth xml_body json_body my_auth debug ec2_extension user_crud_extension public_service
