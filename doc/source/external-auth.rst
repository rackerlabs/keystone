===========================================
Using external authentication with Keystone
===========================================

When Keystone is executed in :doc:`HTTPD <apache-httpd>` it is possible to 
use additional authentication methods different from the authentication
provided by the identity store backend. For example, this makes possible to
use a SQL identity backend together with X.509 authentication, Kerberos, etc.
instead of using the username/password combination.

Given auth
==========

Webservers like Apache HTTP support many ways of authentication. Keystone can
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

Developing a WSGI middleware for authentication
===============================================

Apart from the **Given Authentication** it is possible to implement other
custom authentication mechanisms based on the usage of the ``REMOTE_USER``
variable. Please note that is preferred to leverage the authentication to
the http server and not develop a custom authentication module unless strongly
needed.

This task is accomplished implementing a WSGI middleware. This middleware
should set the ``REMOTE_USER`` variable in the environment and Keystone will
assume that the user has been already authenticated upstream and will not try to
authenticate it. However, as in the given auth case, the user must exist in
advance in the identity backend so that a proper token can be issued.

Your code should set the ``REMOTE_USER`` if the user is properly authenticated,
following the semantics below::

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
                # User is not authenticated
                raise exception.Unauthorized(message="Invalid user")

Pipeline config
--------------

You have to create a filter and then add it to the pipeline. Assuming that your
middleware module is ``keystone.middleware.MyMiddlewareAuth`` you configure it
in your ``keystone.conf`` as::

    [filter:myauth]
    paste.filter_factory = keystone.middleware.MyMiddlewareAuth.factory

    [pipeline:public_api]
    pipeline = stats_monitoring url_normalize token_auth admin_token_auth xml_body json_body myauth debug ec2_extension user_crud_extension public_service


