
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

"""Admin WSGI application.

This file can be imported with `WSGIImportScript`, and also be the script for
`WSGIScriptAlias`.

For example, create a symlink so Apache httpd can serve the script::

  ln -s /opt/stack/keystone/keystone/application/admin.py \
    /var/www/keystone/admin

And define a daemon process for the admin instance in Apache config,
setting the script alias. Optionally, you can import the script with
`WSGIImportScript` which should improve first-time page load.

::

  <VirtualHost *:35357>
      WSGIDaemonProcess keystone-admin processes=5 threads=1 user=keystone
      WSGIProcessGroup keystone-admin
      WSGIScriptAlias / /var/www/keystone/admin
      WSGIApplicationGroup %{GLOBAL}
      WSGIImportScript /opt/stack/keystone/keystone/application/httpd/admin.py
        process-group=keystone-admin application-group=%{GLOBAL}
      ErrorLog /var/log/apache2/keystone
      LogLevel debug
      CustomLog /var/log/apache2/access.log combined
  </VirtualHost>

"""

# Use import here because python ensures it happens only once.
from keystone.application.httpd import admin_app

# NOTE(ldbragst): 'application' is required in this context by WSGI spec.
# The following is a reference to Python Paste Deploy documentation
# http://pythonpaste.org/deploy/
application = admin_app.application
