# vim: tabstop=4 shiftwidth=4 softtabstop=4
# Copyright (c) 2010-2011 OpenStack, LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os
import sys
import logging
import functools
from webob import Response
import keystone.logic.types.fault as fault
from keystone.common import config, wsgi


def is_xml_response(req):
    """Returns True when the request wants an XML response, False otherwise"""
    return "Accept" in req.headers and "application/xml" in req.accept


def is_json_response(req):
    """Returns True when the request wants a JSON response, False otherwise"""
    return "Accept" in req.headers and "application/json" in req.accept


def get_app_root():
    return os.path.abspath(os.path.dirname(__file__))


def get_auth_token(req):
    """Returns the auth token from request headers"""
    return req.headers.get("X-Auth-Token")


def get_auth_user(req):
    """Returns the auth user from request headers"""
    return req.headers.get("X-Auth-User")


def get_auth_key(req):
    """Returns the auth key from request headers"""
    return req.headers.get("X-Auth-Key")


def wrap_error(func):

    @functools.wraps(func)
    def check_error(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as err:
            if isinstance(err, fault.IdentityFault):
                return send_error(err.code, kwargs['req'], err)
            elif isinstance(err, fault.ItemNotFoundFault):
                return send_error(err.code, kwargs['req'], err)
            else:
                logging.exception(err)
                return send_error(500, kwargs['req'],
                                fault.IdentityFault("Unhandled error",
                                                    str(err)))
    return check_error


def get_normalized_request_content(model, req):
    """Initialize a model from json/xml contents of request body"""

    if req.content_type == "application/xml":
        return model.from_xml(req.body)
    elif req.content_type == "application/json":
        return model.from_json(req.body)
    else:
        raise fault.IdentityFault("I don't understand the content type",
                                  code=415)


def send_error(code, req, result):
    content = None

    resp = Response()
    resp.headers['content-type'] = None
    resp.status = code

    if result:
        if is_xml_response(req):
            content = result.to_xml()
            resp.headers['content-type'] = "application/xml"
        else:
            content = result.to_json()
            resp.headers['content-type'] = "application/json"

        resp.content_type_params = {'charset': 'UTF-8'}
        resp.unicode_body = content.decode('UTF-8')

    return resp


def send_result(code, req, result=None):
    content = None

    resp = Response()
    resp.headers['content-type'] = None
    resp.status = code
    if code > 399:
        return resp

    if result:
        if is_xml_response(req):
            content = result.to_xml()
            resp.headers['content-type'] = "application/xml"
        else:
            content = result.to_json()
            resp.headers['content-type'] = "application/json"
        resp.content_type_params = {'charset': 'UTF-8'}
        resp.unicode_body = content.decode('UTF-8')

    return resp


def send_legacy_result(code, headers):
    resp = Response()
    if 'content-type' not in headers:
        headers['content-type'] = "text/plain"

    resp.headers = headers
    resp.status = code
    if code > 399:
        return resp

    resp.content_type_params = {'charset': 'UTF-8'}

    return resp


def import_module(module_name, class_name=None):
    '''Import a class given a full module.class name or seperate
    module and options. If no class_name is given, it is assumed to
    be the last part of the module_name string.'''
    if class_name is None:
        try:
            __import__(module_name)
            return sys.modules[module_name]
        except ImportError as exc:
            module_name, _separator, class_name = module_name.rpartition('.')
            if not exc.args[0].startswith('No module named %s' % class_name):
                raise
    try:
        __import__(module_name)
        return getattr(sys.modules[module_name], class_name)
    except (ImportError, ValueError, AttributeError), exception:
        raise ImportError(_('Class %s.%s cannot be found (%s)') %
            (module_name, class_name, exception))


def check_empty_string(value, message):
    """
    Checks whether a string is empty and raises
    fault for empty string.
    """
    if is_empty_string(value):
        raise fault.BadRequestFault(message)


def is_empty_string(value):
    """
    Checks whether string is empty.
    """
    if value is None:
        return True
    if not isinstance(value, basestring):
        return False
    if len(value.strip()) == 0:
        return True
    return False


class Server():
    """Used to start and stop Keystone servers

    This class is called from shell and command-line scripts and is the
    entry-point for starting and stopping Keystone servers.

    The initializer can take option and argument overrides, but otherwise will
    parse arguments and configuration files itself to determine how to start
    the server.
    """

    def __init__(self, name='admin', config_name=None,
                 options=None, args=None):
        """Initizalizer which takes the following paramaters:

        :param name: A cosmetic name for the server (ex. Admin API)
        :param config: the paste config name to look for when starting the
            server
        :param options: a mapping of option key/str(value) pairs passed to
            config.load_paste_app
        :param args: override for sys.argv (otherwise sys.argv is used)
        """
        self.options = options
        if args:
            self.args = args
        else:
            self.args = sys.argv

        if options is None or args is None:
            # Initialize a parser for our configuration paramaters
            parser = optparse.OptionParser(version='%%prog %s' %
                                           version.version())
            common_group = config.add_common_options(parser)
            config.add_log_options(parser)

            # Parse arguments and load config
            (poptions, pargs) = config.parse_options(parser)

        if options is None:
            self.options = poptions
        else:
            self.options = options

        if args is None:
            self.args = pargs
        else:
            self.args = args

        self.name = name
        self.config = config_name or self.name

    def start(self, host=None, port=None, wait=True):
        """Starts the Keystone server

        :param host: the IP address to listen on
        :param port: the TCP/IP port to listen on
        :param wait: whether to wait (block) for the server to terminate or
            return to the caller without waiting
        """
        # Load Service API server
        conf, app = config.load_paste_app(
            self.config, self.options, self.args)

        debug = self.options.get('debug') or conf.get('debug', False)
        debug = debug in [True, "True", "1"]
        verbose = self.options.get('verbose') or conf.get('verbose', False)
        verbose = verbose in [True, "True", "1"]

        if debug or verbose:
            config_file = config.find_config_file(self.options, self.args)
            print "Starting '%s' with config: %s" % (self.config, config_file)

        if port is None:
            if self.config == 'admin':
                # Legacy
                port = int(self.options.get('bind_port') or
                           conf.get('admin_port', 35357))
            else:
                port = int(self.options.get('bind_port') or
                           conf.get('service_port', 5000))
        if host is None:
            host = self.options.get('bind_host',
                                    conf.get('service_host', '0.0.0.0'))

        self.key = "%s-%s:%s" % (self.name, host, port)

        # Safely get SSL options
        service_ssl = conf.get('service_ssl', False)
        service_ssl = service_ssl in [True, "True", "1"]

        # Load the server
        if service_ssl:
            cert_required = conf.get('cert_required', False)
            cert_required = cert_required in [True, "True", "1"]
            certfile = conf.get('certfile')
            keyfile = conf.get('keyfile')
            ca_certs = conf.get('ca_certs')

            self.server = wsgi.SslServer()
            self.server.start(app, port, host,
                         certfile=certfile, keyfile=keyfile,
                         ca_certs=ca_certs,
                         cert_required=cert_required,
                         key=self.key)
        else:
            self.server = wsgi.Server()
            self.server.start(app, port, host,
                              key="%s-%s:%s" % (self.config, host, port))

        print "%s listening on %s://%s:%s" % (
            self.name, ['http', 'https'][service_ssl], host, port)

        # Wait until done
        if wait:
            self.server.wait()

    def stop(self):
        """Stops the Keystone server

        This should be called always to release the network socket
        """
        if self.server is not None:
            if self.key in self.server.threads:
                self.server.threads[self.key].kill()
            self.server = None
