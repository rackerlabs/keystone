# Copyright 2016 Massachusetts Open Cloud
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

FROM unicon/shibboleth-idp

MAINTAINER openstack-dev@openstack.org

RUN rm -rf /opt/shibboleth-idp/conf && \
    rm -rf /opt/shibboleth-idp/credentials && \
    rm -rf /opt/shibboleth-idp/metadata && \
    rm -rf /opt/shibboleth-idp/webapp && \
    rm -rf /opt/shibboleth-idp/views

ADD config/conf /opt/shibboleth-idp/conf
ADD config/credentials /opt/shibboleth-idp/credentials
ADD config/metadata /opt/shibboleth-idp/metadata
ADD config/webapp /opt/shibboleth-idp/webapp
ADD config/views /opt/shibboleth-idp/views
