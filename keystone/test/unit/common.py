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


import unittest2 as unittest
import httplib2
import json
from lxml import etree
import uuid

URL_V1 = 'http://localhost:5000/v1.0/'
URL_V2 = 'http://localhost:5001/v2.0/'


def get_token(username, password, tenant_id, kind=''):
    header = httplib2.Http(".cache")
    url = '%stokens' % URL_V2

    body = {
        "passwordCredentials": {
            "username": username,
            "password": password}}

    if tenant_id:
        body["passwordCredentials"]["tenantId"] = tenant_id

    resp, content = header.request(url, "POST", body=json.dumps(body),
        headers={"Content-Type": "application/json"})

    if int(resp['status']) == 200:
        content = json.loads(content)
        token = str(content['auth']['token']['id'])
    else:
        token = None
    if kind == 'token':
        return token
    else:
        return (resp, content)


def get_token_legacy(user, pswd, kind=''):
    header = httplib2.Http(".cache")
    url = URL_V1
    resp, content = header.request(url, "GET", '',
                              headers={"Content-Type": "application/json",
                                       "X-Auth-User": user,
                                       "X-Auth-Key": pswd})

    if int(resp['status']) == 204:
        token = resp['x-auth-token']
    else:
        token = None
    if kind == 'token':
        return token
    else:
        return (resp, content)


def delete_token(token, admin_token):
    header = httplib2.Http(".cache")
    url = '%stoken/%s' % (URL_V2, token)
    resp, content = header.request(url, "DELETE", body='',
                              headers={"Content-Type": "application/json",
                                       "X-Auth-Token": admin_token})
    return (resp, content)


def create_tenant_json(tenant_name, admin_token):
    header = httplib2.Http(".cache")

    url = '%stenants' % (URL_V2)
    body = {
        "tenant": {
            "name": tenant_name,
            "description": "A description ...",
            "enabled": True}}

    return header.request(url, "POST", body=json.dumps(body), headers={
        "Content-Type": "application/json",
        "X-Auth-Token": admin_token})

def create_tenant(tenant_name, admin_token):
    resp, content = create_tenant_json(tenant_name, admin_token)
    return json.loads(content)['tenant']['id']

def delete_tenant(tenant_id, admin_token):
    header = httplib2.Http(".cache")
    url = '%stenants/%s' % (URL_V2, tenant_id)
    resp, _content = header.request(url, "DELETE", body='{}',
                              headers={"Content-Type": "application/json",
                                       "X-Auth-Token": admin_token})
    return resp


def get_token_xml(user, pswd, tenant_id, return_type=''):
    header = httplib2.Http(".cache")
    url = '%stokens' % URL_V2
    body = '<?xml version="1.0" encoding="UTF-8"?> \
                <passwordCredentials \
                xmlns="http://docs.openstack.org/identity/api/v2.0" \
                password="%s" username="%s" \
                tenantId="%s"/> ' % (pswd, user, tenant_id)
    resp, content = header.request(url, "POST", body=body,
                              headers={"Content-Type": "application/xml",
                                     "ACCEPT": "application/xml"})
    if int(resp['status']) == 200:
        dom = etree.fromstring(content)
        root = dom.find("{http://docs.openstack.org/" \
                        "identity/api/v2.0}token")
        token_root = root.attrib
        token = str(token_root['id'])
    else:
        token = None

    if return_type == 'token':
        return token
    else:
        return (resp, content)


def delete_token_xml(token, admin_token):
    header = httplib2.Http(".cache")
    url = '%stoken/%s' % (URL_V2, token)
    resp, content = header.request(url, "DELETE", body='',
                              headers={"Content-Type": "application/xml",
                                       "X-Auth-Token": admin_token,
                                       "ACCEPT": "application/xml"})
    return (resp, content)


def create_tenant_xml(tenantid, admin_token):
    header = httplib2.Http(".cache")
    url = '%stenants' % (URL_V2)
    body = '<?xml version="1.0" encoding="UTF-8"?> \
            <tenant xmlns="http://docs.openstack.org/identity/api/v2.0" \
            enabled="true" id="%s"> \
            <description>A description...</description> \
            </tenant>' % tenantid
    resp, content = header.request(url, "POST", body=body,
                              headers={"Content-Type": "application/xml",
                                       "X-Auth-Token": admin_token,
                                       "ACCEPT": "application/xml"})
    return (resp, content)


def delete_tenant_xml(tenantid, admin_token):
    header = httplib2.Http(".cache")
    url = '%stenants/%s' % (URL_V2, tenantid)
    resp, _content = header.request(url, "DELETE", body='',
                              headers={"Content-Type": "application/xml",
                                       "X-Auth-Token": admin_token,
                                       "ACCEPT": "application/xml"})

    return resp


def create_user_xml(tenant_id, username, admin_token, email=None,
        password='secrete'):
    header = httplib2.Http(".cache")
    url = '%susers' % (URL_V2)
    email = email or "%s@openstack.org" % (username,)
    body = '<?xml version="1.0" encoding="UTF-8"?> \
            <user xmlns="http://docs.openstack.org/identity/api/v2.0" \
            email="%s" tenantId="%s" name="%s" enabled="true" \
            password="%s"/>' % (email, tenant_id, username, password)
    resp, content = header.request(url, "POST", body=body,
                              headers={"Content-Type": "application/xml",
                                       "X-Auth-Token": admin_token,
                                       "ACCEPT": "application/xml"})
    return (resp, content)


def create_user_json(tenant_id, username, admin_token, email=None,
        password='secrete'):
    header = httplib2.Http(".cache")
    url = '%susers' % (URL_V2)
    email = email or "%s@openstack.org" % (username,)
    body = {
        "user": {
            "password": password,
            "name": username,
            "tenantId": tenant_id,
            "email": "%s" % email,
            "enabled": True}}
    return header.request(url, "POST", body=json.dumps(body), headers={
        "Content-Type": "application/json",
        "X-Auth-Token": admin_token})


def delete_user(user_id, admin_token):
    header = httplib2.Http(".cache")
    url = '%susers/%s' % (URL_V2, user_id)
    resp, _content = header.request(url, "DELETE", body='{}',
                              headers={"Content-Type": "application/json",
                                       "X-Auth-Token": admin_token})
    return resp


def delete_user_xml(userid, admin_token):
    header = httplib2.Http(".cache")
    url = '%susers/%s' % (URL_V2, userid)
    resp, _content = header.request(url, "DELETE", body='',
                              headers={"Content-Type": "application/xml",
                                       "X-Auth-Token": admin_token,
                                       "ACCEPT": "application/xml"})
    return resp


def add_user_xml(userid, admin_token):
    header = httplib2.Http(".cache")
    url = '%susers/%s/add' % (URL_V2, userid)
    resp, content = header.request(url, "PUT", body='{}',
                              headers={"Content-Type": "application/xml",
                                       "X-Auth-Token": admin_token,
                                       "ACCEPT": "application/xml"})
    return (resp, content)


def add_user_json(admin_token):
    header = httplib2.Http(".cache")
    url = '%susers/' % (URL_V2)
    resp, content = header.request(url, "PUT", body='{}',
                              headers={"Content-Type": "application/json",
                                       "X-Auth-Token": admin_token})
    return (resp, content)


def user_set_enabled(admin_token, user_id, enabled=True):
    header = httplib2.Http(".cache")
    url = '%susers/%s/enabled' % (URL_V2, user_id)
    data = '{"user": { "enabled": %s}}' % ("true" if enabled else "false")
    resp, content = header.request(url, "PUT", body=data, headers={
        "Content-Type": "application/json",
        "X-Auth-Token": admin_token})
    return (resp, content)


def user_update_json(admin_token, user_id, email):
    header = httplib2.Http(".cache")
    url = '%susers/%s' % (URL_V2, user_id)
    data = '{"user": { "email": "%s"}}' % (email)
    resp, content = header.request(url, "PUT", body=data, headers={
        "Content-Type": "application/json",
        "X-Auth-Token": admin_token})
    return (resp, content)


def user_update_xml(admin_token, user_id, email):
    header = httplib2.Http(".cache")
    url = '%susers/%s' % (URL_V2, user_id)
    data = '<?xml version="1.0" encoding="UTF-8"?> \
            <user xmlns="http://docs.openstack.org/identity/api/v2.0" \
            email="%s" />' % (email)
    resp, content = header.request(url, "PUT", body=data, headers={
        "Content-Type": "application/xml",
        "X-Auth-Token": admin_token,
        "ACCEPT": "application/xml"})
    return (resp, content)


def user_get_json(user_id, admin_token):
    header = httplib2.Http(".cache")
    url = '%susers/%s' % (URL_V2, user_id)
    #test for Content-Type = application/json
    resp, content = header.request(url, "GET", body='{}',
                              headers={"Content-Type": "application/json",
                                       "X-Auth-Token": admin_token})
    return (resp, content)


def user_password_json(user_id, admin_token):
    header = httplib2.Http(".cache")
    url = '%susers/%s/password' % (URL_V2, user_id)
    data = '{"user": { "password": "p@ssword"}}'
    resp, content = header.request(url, "PUT", body=data,
                              headers={"Content-Type": "application/json",
                                       "X-Auth-Token": admin_token})
    return (resp, content)


def user_password_xml(user_id, admin_token):
    header = httplib2.Http(".cache")
    url = '%susers/%s/password' % (URL_V2, user_id)
    data = '<?xml version="1.0" encoding="UTF-8"?> \
            <user xmlns="http://docs.openstack.org/identity/api/v2.0" \
            password="p@ssword" />'
    resp, content = header.request(url, "PUT", body=data,
                              headers={"Content-Type": "application/xml",
                                       "X-Auth-Token": admin_token,
                                       "ACCEPT": "application/xml"})
    return (resp, content)


def user_enabled_json(user_id, admin_token):
    header = httplib2.Http(".cache")
    url = '%susers/%s/enabled' % (URL_V2, user_id)
    data = {"user": {"enabled": True}}
    resp, content = header.request(url, "PUT", body=json.dumps(data),
                              headers={"Content-Type": "application/json",
                                       "X-Auth-Token": admin_token})
    return (resp, content)


def user_enabled_xml(user_id, admin_token):
    header = httplib2.Http(".cache")
    url = '%susers/%s/enabled' % (URL_V2, user_id)
    data = '<?xml version="1.0" encoding="UTF-8"?> \
            <user xmlns="http://docs.openstack.org/identity/api/v2.0" \
            enabled="true" />'
    resp, content = header.request(url, "PUT", body=data,
                              headers={"Content-Type": "application/xml",
                                       "X-Auth-Token": admin_token,
                                       "ACCEPT": "application/xml"})
    return (resp, content)


def user_tenant_update_json(user_id, tenant_id, admin_token):
    header = httplib2.Http(".cache")
    url = '%susers/%s/tenant' % (URL_V2, user_id)
    data = {"user": {"tenantId": tenant_id}}
    resp, content = header.request(url, "PUT", body=json.dumps(data),
                              headers={"Content-Type": "application/json",
                                       "X-Auth-Token": admin_token})
    return (resp, content)


def user_tenant_update_xml(user_id, tenant_id, admin_token):
    header = httplib2.Http(".cache")
    url = '%susers/%s/tenant' % (URL_V2, user_id)
    data = '<?xml version="1.0" encoding="UTF-8"?> \
            <user xmlns="http://docs.openstack.org/identity/api/v2.0" \
            tenantId="%s" />' % (tenant_id)
    resp, content = header.request(url, "PUT", body=data,
                              headers={"Content-Type": "application/xml",
                                       "X-Auth-Token": admin_token,
                                       "ACCEPT": "application/xml"})
    return (resp, content)


def user_get_xml(user_id, admin_token):
    header = httplib2.Http(".cache")
    url = '%susers/%s' % (URL_V2, user_id)
    resp, content = header.request(url, "GET", body='{}',
                              headers={"Content-Type": "application/xml",
                                       "X-Auth-Token": admin_token,
                                       "ACCEPT": "application/xml"})
    return (resp, content)


def users_get_json(user_id, admin_token):
    header = httplib2.Http(".cache")
    url = '%susers/%s' % (URL_V2, user_id)
    resp, content = header.request(url, "GET", body='{}',
                              headers={"Content-Type": "application/json",
                                       "X-Auth-Token": admin_token})
    return (resp, content)


def users_get_all_xml(admin_token):
    header = httplib2.Http(".cache")
    url = '%susers' % (URL_V2)
    resp, content = header.request(url, "GET", body='{}',
                              headers={"Content-Type": "application/xml",
                                       "X-Auth-Token": admin_token,
                                       "ACCEPT": "application/xml"})
    return (resp, content)


def users_get_all_json(admin_token):
    header = httplib2.Http(".cache")
    url = '%susers' % (URL_V2)
    resp, content = header.request(url, "GET", body='{}',
                              headers={"Content-Type": "application/json",
                                       "X-Auth-Token": admin_token})
    return (resp, content)


def users_get_xml(tenant_id, admin_token):
    header = httplib2.Http(".cache")
    url = '%susers/%s' % (URL_V2, tenant_id)
    resp, content = header.request(url, "GET", body='{}',
                              headers={"Content-Type": "application/xml",
                                       "X-Auth-Token": admin_token,
                                       "ACCEPT": "application/xml"})
    return (resp, content)


def create_role(roleid, admin_token):
    header = httplib2.Http(".cache")

    url = '%sroles' % (URL_V2)
    body = {"role": {"id": roleid,
                       "description": "A description ..."}}
    resp, content = header.request(url, "POST", body=json.dumps(body),
                              headers={"Content-Type": "application/json",
                                       "X-Auth-Token": admin_token})
    return (resp, content)


def create_role_mapped_to_service(role_id, admin_token, service_id):
    header = httplib2.Http(".cache")

    url = '%sroles' % (URL_V2)
    body = {"role": {"id": role_id,
                       "description": "A description ...",
                       "serviceId": service_id}}
    resp, content = header.request(url, "POST", body=json.dumps(body),
                              headers={"Content-Type": "application/json",
                                       "X-Auth-Token": admin_token})
    return (resp, content)


def create_role_mapped_to_service_xml(role_id, admin_token, service_id):
    header = httplib2.Http(".cache")

    url = '%sroles' % (URL_V2)
    body = '<?xml version="1.0" encoding="UTF-8"?>\
        <role xmlns="http://docs.openstack.org/identity/api/v2.0" \
        id="%s" description="A Description of the role" serviceId="%s"/>\
                ' % (role_id, service_id)
    resp, content = header.request(url, "POST", body=body,
                              headers={"Content-Type": "application/xml",
                                       "X-Auth-Token": admin_token})
    return (resp, content)


def get_role(role_id, admin_token):
    header = httplib2.Http(".cache")
    url = '%sroles/%s' % (URL_V2, role_id)
    resp, content = header.request(url, "GET", body='',
        headers={"Content-Type": "application/json",
            "X-Auth-Token": admin_token,
                "ACCEPT": "application/json",
                })
    return (resp, content)


def get_role_xml(role_id, admin_token):
    header = httplib2.Http(".cache")
    url = '%sroles/%s' % (URL_V2, role_id)
    resp, content = header.request(url, "GET", body='',
        headers={"Content-Type": "application/xml",
            "X-Auth-Token": admin_token,
                "ACCEPT": "application/xml",
                })
    return (resp, content)


def create_role_ref(user_id, role_id, tenant_id, admin_token):
    header = httplib2.Http(".cache")

    url = '%susers/%s/roleRefs' % (URL_V2, user_id)
    body = {"roleRef": {"tenantId": tenant_id,
                       "roleId": role_id}}
    resp, content = header.request(url, "POST", body=json.dumps(body),
                              headers={"Content-Type": "application/json",
                                       "X-Auth-Token": admin_token})
    return (resp, content)


def create_role_ref_xml(user_id, role_id, tenant_id, admin_token):
    header = httplib2.Http(".cache")
    url = '%susers/%s/roleRefs' % (URL_V2, user_id)
    body = '<?xml version="1.0" encoding="UTF-8"?>\
            <roleRef xmlns="http://docs.openstack.org/identity/api/v2.0" \
            tenantId="%s" roleId="%s"/>\
                    ' % (tenant_id, role_id)
    resp, content = header.request(url, "POST", body=body,
                              headers={"Content-Type": "application/xml",
                                       "X-Auth-Token": admin_token,
                                       "ACCEPT": "application/xml"})
    return (resp, content)


def delete_role_ref(user, role_ref_id, admin_token):
    header = httplib2.Http(".cache")
    url = '%susers/%s/roleRefs/%s' % (URL_V2, user, role_ref_id)
    resp, content = header.request(url, "DELETE", body='',
                              headers={"Content-Type": "application/json",
                                       "X-Auth-Token": admin_token})
    return (resp, content)


def create_role_xml(role_id, admin_token):
    header = httplib2.Http(".cache")
    url = '%sroles' % (URL_V2)
    body = '<?xml version="1.0" encoding="UTF-8"?>\
            <role xmlns="http://docs.openstack.org/identity/api/v2.0" \
            id="%s" description="A Description of the role"/>\
                    ' % role_id
    resp, content = header.request(url, "POST", body=body,
                              headers={"Content-Type": "application/xml",
                                       "X-Auth-Token": admin_token,
                                       "ACCEPT": "application/xml"})
    return (resp, content)


def delete_role(role_id, admin_token):
    header = httplib2.Http(".cache")
    url = '%sroles/%s' % (URL_V2, role_id)
    resp, content = header.request(url, "DELETE", body='',
                              headers={"Content-Type": "application/json",
                                       "X-Auth-Token": admin_token})
    return resp, content


def create_service(service_id, admin_token):
    header = httplib2.Http(".cache")

    url = '%sservices' % (URL_V2)
    body = {"service": {"id": service_id,
                       "description": "A description ..."}}
    resp, content = header.request(url, "POST", body=json.dumps(body),
                              headers={"Content-Type": "application/json",
                                       "X-Auth-Token": admin_token})
    return (resp, content)


def create_service_xml(service_id, admin_token):
    header = httplib2.Http(".cache")
    url = '%sservices' % (URL_V2)
    body = '<?xml version="1.0" encoding="UTF-8"?>\
            <service xmlns="http://docs.openstack.org/identity/api/v2.0" \
            id="%s" description="A Description of the service"/>\
                    ' % service_id
    resp, content = header.request(url, "POST", body=body,
                              headers={"Content-Type": "application/xml",
                                       "X-Auth-Token": admin_token,
                                       "ACCEPT": "application/xml"})
    return (resp, content)


def delete_service(service_id, admin_token):
    header = httplib2.Http(".cache")
    url = '%sservices/%s' % (URL_V2, service_id)
    resp, content = header.request(url, "DELETE", body='',
                              headers={"Content-Type": "application/json",
                                       "X-Auth-Token": admin_token})
    return resp, content


def get_services(admin_token):
    header = httplib2.Http(".cache")
    url = '%sservices' % (URL_V2)
    #test for Content-Type = application/json
    resp, content = header.request(url, "GET", body='{}',
                              headers={"Content-Type": "application/json",
                                     "X-Auth-Token": admin_token})
    return (resp, content)


def get_services_xml(admin_token):
    header = httplib2.Http(".cache")
    url = '%sservices' % (URL_V2)
    #test for Content-Type = application/xml
    resp, content = header.request(url, "GET", body='{}',
                              headers={"Content-Type": "application/xml",
                                     "X-Auth-Token": admin_token,
                                     "ACCEPT": "application/xml"})
    return (resp, content)


def get_service(service_id, admin_token):
    header = httplib2.Http(".cache")
    url = '%sservices/%s' % (URL_V2, service_id)
    #test for Content-Type = application/json
    resp, content = header.request(url, "GET", body='{}',
                              headers={"Content-Type": "application/json",
                                     "X-Auth-Token": admin_token})
    return (resp, content)


def get_service_xml(service_id, admin_token):
    header = httplib2.Http(".cache")
    url = '%sservices/%s' % (URL_V2, service_id)
    #test for Content-Type = application/xml
    resp, content = header.request(url, "GET", body='{}',
                              headers={"Content-Type": "application/xml",
                                     "X-Auth-Token": admin_token,
                                     "ACCEPT": "application/xml"})
    return (resp, content)


def create_endpoint(tenant_id, endpoint_templates_id, admin_token):
    header = httplib2.Http(".cache")

    url = '%stenants/%s/endpoints' % (URL_V2, tenant_id)
    body = {"endpointTemplate": {"id": endpoint_templates_id}}
    resp, content = header.request(url, "POST", body=json.dumps(body),
                              headers={"Content-Type": "application/json",
                                       "X-Auth-Token": admin_token})
    return (resp, content)


def create_endpoint_xml(tenant_id, endpoint_templates_id, admin_token):
    header = httplib2.Http(".cache")
    url = '%stenants/%s/endpoints' % (URL_V2, tenant_id)
    body = '<?xml version="1.0" encoding="UTF-8"?>\
        <endpointTemplate xmlns="http://docs.openstack.org/identity/api/v2.0" \
        id="%s"/>' % (endpoint_templates_id)
    resp, content = header.request(url, "POST", body=body,
                              headers={"Content-Type": "application/xml",
                                       "X-Auth-Token": admin_token,
                                       "ACCEPT": "application/xml"})
    return (resp, content)


def delete_endpoint(tenant, endpoint_id, admin_token):
    header = httplib2.Http(".cache")
    url = '%stenants/%s/endpoints/%s' % (URL_V2, tenant, endpoint_id)
    resp, _content = header.request(url, "DELETE", body='', headers={
        "Content-Type": "application/json",
        "X-Auth-Token": admin_token})
    return (resp, _content)


def delete_all_endpoint(tenant_id, admin_token):
    header = httplib2.Http(".cache")
    url = '%stenants/%s/endpoints' % (URL_V2, tenant_id)
    #test for Content-Type = application/json
    resp, content = header.request(url, "GET", body='{}',
                              headers={"Content-Type": "application/json",
                                     "X-Auth-Token": admin_token})
    if int(resp['status']) == 500:
        assert False
    elif int(resp['status']) == 503:
        assert False

    #verify content
    obj = json.loads(content)
    try:
        endpoints = obj["endpoints"]["values"]
    except KeyError:
        pass
    else:
        for endpoint in endpoints:
            delete_endpoint(tenant_id, endpoint["id"], admin_token)


def create_endpoint_template(region, service,
    public_url, admin_url, internal_url, enabled, is_global, admin_token):
    header = httplib2.Http(".cache")

    url = '%sendpointTemplates' % (URL_V2)
    body = {"endpointTemplate": {"region": region,
                       "serviceId": service,
                       "publicURL": public_url,
                       "adminURL": admin_url,
                       "internalURL": internal_url,
                       "enabled": enabled,
                       "global": is_global}}
    resp, content = header.request(url, "POST", body=json.dumps(body),
                              headers={"Content-Type": "application/json",
                                       "X-Auth-Token": admin_token})
    return (resp, content)


def create_endpoint_template_xml(region, service, public_url, admin_url,
    internal_url, enabled, is_global, admin_token):
    header = httplib2.Http(".cache")

    url = '%sendpointTemplates' % (URL_V2)
    body = ('<?xml version="1.0" encoding="UTF-8"?> '
        '<endpointTemplate '
        'xmlns="http://docs.openstack.org/identity/api/v2.0" '
        'region="%s" '
        'serviceId="%s" '
        'publicURL="%s" '
        'adminURL="%s" '
        'internalURL="%s" '
        'enabled="%s" '
        'global="%s"/>' % (region, service, public_url, admin_url,
            internal_url, enabled, is_global))
    body = {"endpointTemplate": {"region": region,
                       "serviceId": service,
                       "publicURL": public_url,
                       "adminURL": admin_url,
                       "internalURL": internal_url,
                       "enabled": enabled,
                       "global": is_global}}
    resp, content = header.request(url, "POST", body=json.dumps(body),
                              headers={"Content-Type": "application/json",
                                       "X-Auth-Token": admin_token,
                                       "ACCEPT": "application/xml"})
    return (resp, content)


def delete_endpoint_template(endpoint_template_id, admin_token):
    header = httplib2.Http(".cache")
    url = '%sendpointTemplates/%s' % (URL_V2, endpoint_template_id)
    resp, content = header.request(url, "DELETE", body='',
                              headers={"Content-Type": "application/json",
                                       "X-Auth-Token": admin_token})
    return resp, content


def update_endpoint_template(endpoint_template_id, region, service,
    public_url, admin_url, internal_url, enabled, is_global, admin_token):
    header = httplib2.Http(".cache")

    url = '%sendpointTemplates/%s' % (URL_V2, endpoint_template_id)
    body = {"endpointTemplate": {"region": region,
                       "serviceId": service,
                       "publicURL": public_url,
                       "adminURL": admin_url,
                       "internalURL": internal_url,
                       "enabled": enabled,
                       "global": is_global}}
    resp, content = header.request(url, "PUT", body=json.dumps(body),
                              headers={"Content-Type": "application/json",
                                       "X-Auth-Token": admin_token})
    return (resp, content)


def update_endpoint_template_xml(endpoint_template_id, region, service,
    public_url, admin_url,
    internal_url, enabled, is_global, admin_token):
    header = httplib2.Http(".cache")

    url = '%sendpointTemplates/%s' % (URL_V2, endpoint_template_id)
    body = '<?xml version="1.0" encoding="UTF-8"?>\
        <endpointTemplate xmlns="http://docs.openstack.org/identity/api/v2.0" \
        region="%s" serviceId="%s" \
        publicURL="%s" adminURL="%s"\
        internalURL="%s" enabled="%s"\
        global="%s"/>' % (region, service, public_url, \
        admin_url, internal_url, enabled, is_global)
    body = {"endpointTemplate": {"region": region,
                       "serviceId": service,
                       "publicURL": public_url,
                       "adminURL": admin_url,
                       "internalURL": internal_url,
                       "enabled": enabled,
                       "global": is_global}}
    resp, content = header.request(url, "PUT", body=json.dumps(body),
                              headers={"Content-Type": "application/json",
                                       "X-Auth-Token": admin_token,
                                       "ACCEPT": "application/xml"})
    return (resp, content)


def get_endpoint_template(endpoint_template_id, admin_token):
    header = httplib2.Http(".cache")
    url = '%sendpointTemplates/%s' % (URL_V2, endpoint_template_id)
    #test for Content-Type = application/json
    resp, content = header.request(url, "GET", body='{}',
        headers={"Content-Type": "application/json",
        "X-Auth-Token": admin_token})
    return (resp, content)


def content_type(resp):
    return resp['content-type'].split(';')[0]

def get_global_tenant():
    return 'GlobalTenant'

def unique_str():
    """Returns a unique string on each call"""
    return str(uuid.uuid4())

class FunctionalTest(unittest.TestCase):
    """Base functional test case for Keystone"""
    admin_token = str('999888777666')
    service_token = None
    exp_auth_token = str('000999')
    disabled_token = str('999888777')
    missing_token = str('')
    invalid_token = str('invalid_token')

    def setUp(self):
        self.service_id = unique_str()
        self.service_role = self.service_id + ':test_role'

        self.tenant_name = unique_str()

        self.user_id = None
        self.user_name = unique_str()
        self.user_password = unique_str()
        self.user_email = self.user_name + '@openstack.org'

        self.disabled_user_id = None
        self.disabled_user_name = unique_str()
        self.disabled_user_password = unique_str()
        self.disabled_user_email = self.disabled_user_name + '@openstack.org'

        # Create a tenant
        self.tenant_id = self.create_tenant(self.tenant_name)

        # Create a user attached to the above tenant
        self.user_id = self.create_user(self.user_name, self.user_password,
            self.user_email, self.tenant_id)

        # Authenticate the above user for his tenant
        self.service_token = get_token(self.user_name, self.user_password,
            self.tenant_id, 'token')

        # Create and disable a user
        self.disabled_user_id = self.create_user(self.disabled_user_name,
            self.user_password, self.disabled_user_email, self.tenant_id)
        user_set_enabled(self.admin_token, self.disabled_user_id,
            enabled=False)

    def tearDown(self):
        delete_token(self.service_token, self.admin_token)
        self.delete_user(self.user_id, self.admin_token)
        delete_tenant(self.tenant_id, self.admin_token)

    def assertStatusCode(self, code, resp, content):
        self.assertEqual(code, int(resp['status']), (resp, content))

    def assertContentType(self, content_type, resp, content):
        self.assertEqual(content_type, resp['content-type'].split(';')[0],
            (resp, content))

    # User shortcuts

    def create_user(self, username, password, email, tenant_id):
        resp, content = create_user_json(tenant_id, username, self.admin_token,
            email, password)
        self.assertStatusCode(201, resp, content)
        self.assertContentType('application/json', resp, content)
        return json.loads(content)['user']['id']

    def delete_user(self, user_id):
        header = httplib2.Http(".cache")
        url = '%susers/%s' % (URL_V2, user_id)
        resp, content = header.request(url, "DELETE", body='{}', headers={
            "Content-Type": "application/json",
            "X-Auth-Token": self.admin_token})
        self.assertStatusCode(2000, resp, content)
        self.assertContentType('application/json', resp, content)
        return resp, content

    # Tenant shortcuts

    def create_tenant(self, tenant_name):
        resp, content = create_tenant_json(tenant_name, self.admin_token)
        self.assertStatusCode(201, resp, content)
        self.assertContentType('application/json', resp, content)
        return json.loads(content)['tenant']['id']

if __name__ == '__main__':
    unittest.main()
