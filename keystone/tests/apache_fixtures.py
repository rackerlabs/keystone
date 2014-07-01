# Copyright 2014 OpenStack Foundation
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

# Sample SSL environment variables set by Apache mod_ssl when 2-way SSL
# is used to establish the connection.
SSL_ENVIRONMENT = {
    'SSL_SERVER_I_DN_OU': 'Keystone',
    'SSL_SERVER_S_DN_Email': 'keystone@openstack.org',
    'SSL_SERVER_A_KEY': 'rsaEncryption',
    'SSL_SERVER_S_DN': ('CN=localhost,emailAddress=keystone@openstack.org,'
                        'OU=Keystone,O=OpenStack,L=Sunnyvale,ST=CA,C=US'),
    'SSL_SERVER_V_START': 'Jun 30 21:35:59 2014 GMT',
    'SSL_SESSION_ID': 'e72bd347eaffddf4a0fa6b7839ce090772d0617614e11342dc4d',
    'SSL_CLIENT_V_START': 'Jun 30 21:35:59 2014 GMT',
    'wsgi.url_scheme': 'https',
    'SSL_CLIENT_S_DN_ST': 'CA',
    'SSL_CLIENT_A_KEY': 'rsaEncryption',
    'SSL_SERVER_I_DN_Email': 'keystone@openstack.org',
    'SSL_CLIENT_S_DN_CN': 'localhost',
    'SSL_CLIENT_I_DN_Email': 'keystone@openstack.org',
    'SSL_SERVER_S_DN_ST': 'CA',
    'SSL_CIPHER': 'ECDHE-RSA-AES256-GCM-SHA384',
    'SSL_TLS_SNI': 'localhost',
    'SSL_CLIENT_I_DN_ST': 'CA',
    'SSL_CLIENT_VERIFY': 'SUCCESS',
    'SSL_SECURE_RENEG': 'true',
    'SSL_CLIENT_I_DN_C': 'US',
    'SSL_CLIENT_S_DN_O': 'OpenStack',
    'SSL_CLIENT_S_DN_L': 'Sunnyvale',
    'SSL_CLIENT_S_DN_C': 'US',
    'SSL_CLIENT_I_DN_L': 'Sunnyvale',
    'SSL_CLIENT_I_DN_O': 'OpenStack',
    'SSL_SERVER_M_SERIAL': '10',
    'REQUEST_SCHEME': 'https',
    'SSL_CLIENT_I_DN_CN': 'Self Signed',
    'SSL_SERVER_S_DN_CN': 'localhost',
    'SSL_VERSION_INTERFACE': 'mod_ssl/2.4.7',
    'SSL_CLIENT_M_VERSION': '1',
    'SSL_CLIENT_S_DN_Email': 'keystone@openstack.org',
    'SSL_SERVER_I_DN_ST': 'CA',
    'SSL_CIPHER_ALGKEYSIZE': '256',
    'SSL_COMPRESS_METHOD': 'NULL',
    'SSL_SERVER_I_DN_L': 'Sunnyvale',
    'SSL_SERVER_I_DN_O': 'OpenStack',
    'SSL_SERVER_I_DN_C': 'US',
    'SSL_VERSION_LIBRARY': 'OpenSSL/1.0.1f',
    'SSL_SERVER_A_SIG': 'sha256WithRSAEncryption',
    'HTTP_HOST': 'localhost:35357',
    'SSL_SERVER_M_VERSION': '1',
    'REQUEST_URI': '/v3/auth/tokens',
    'SSL_CLIENT_S_DN_OU': 'Keystone',
    'SSL_SERVER_I_DN_CN': 'Self Signed',
    'SSL_CLIENT_M_SERIAL': '10',
    'SSL_SERVER_I_DN': ('CN=Self Signed,emailAddress=keystone@openstack.org,'
                        'OU=Keystone,O=OpenStack,L=Sunnyvale,ST=CA,C=US,'
                        'serialNumber=5'),
    'SSL_CIPHER_EXPORT': 'false',
    'SSL_CLIENT_I_DN_OU': 'Keystone',
    'SSL_CLIENT_S_DN': ('CN=localhost,emailAddress=keystone@openstack.org,'
                        'OU=Keystone,O=OpenStack,L=Sunnyvale,ST=CA,C=US'),
    'SSL_CLIENT_I_DN': ('CN=Self Signed,emailAddress=keystone@openstack.org,'
                        'OU=Keystone,O=OpenStack,L=Sunnyvale,ST=CA,C=US,'
                        'serialNumber=5'),
    'SSL_CLIENT_V_REMAIN': '21360',
    'SERVER_NAME': 'localhost',
    'SSL_CLIENT_A_SIG': 'sha256WithRSAEncryption',
    'SSL_SERVER_S_DN_OU': 'Keystone',
    'SSL_SESSION_RESUMED': 'Initial',
    'SSL_SERVER_S_DN_O': 'OpenStack',
    'SSL_SERVER_S_DN_L': 'Sunnyvale',
    'SSL_SERVER_S_DN_C': 'US',
    'SSL_PROTOCOL': 'TLSv1.2',
    'SSL_SERVER_V_END': 'Dec 22 21:35:59 2072 GMT',
    'SSL_CIPHER_USEKEYSIZE': '256',
    'REMOTE_USER': 'localhost'}
