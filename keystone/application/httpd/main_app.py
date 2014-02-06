
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


"""WSGI Main/Public Application

This file could be used with `WSGIScriptAlias`, but since it can't be used
with `WSGIImportScript`, :class:`keystone.application.httpd.admin` should be
used for both.

"""


from keystone.application.httpd import common


application = common.create_application('main')
