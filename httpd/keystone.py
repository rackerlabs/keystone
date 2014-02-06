# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack Foundation
#
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


"""WSGI application.

This file is *NOT* safe to use with Apache httpd's `WSGIImport`. See
:class:`keystone.application.httpd.admin` and
:class:`keystone.application.httpd.public` for scripts that can be safely
used with `WSGIImport`.

"""

import os

from keystone.application.httpd import common


name = os.path.basename(__file__)

# NOTE(ldbragst): 'application' is required in this context by WSGI spec.
# The following is a reference to Python Paste Deploy documentation
# http://pythonpaste.org/deploy/
application = common.create_application(name)
