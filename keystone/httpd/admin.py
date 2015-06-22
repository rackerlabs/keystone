
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from keystone.server import wsgi as wsgi_server


# NOTE(blk-u): The next line allows the docs to build. when this is run in
# mod_wsgi, the name is like _mod_wsgi_<something>. When docs try to build the
# name is like keystone.httpd.admin.
if __name__.startswith('_mod_wsgi'):

    # NOTE(ldbragst): 'application' is required in this context by WSGI spec.
    # The following is a reference to Python Paste Deploy documentation
    # http://pythonpaste.org/deploy/
    application = wsgi_server.initialize_application('admin')
