# vim: tabstop=4 shiftwidth=4 softtabstop=4


import ldap.filter
import sys

import uuid


from keystone import identity
from keystone import config
from keystone.common import utils
from  keystone.common.ldap import fakeldap, LDAPWrapper 
from  keystone.common.ldap import BaseLdapAPI 

from keystone.identity import models



CONF = config.CONF


def _filter_user(user_ref):
    if user_ref:
        user_ref.pop('password', None)
    return user_ref

class Identity(identity.Driver):

    
    def __init__(self):
        super(Identity, self).__init__()
        self.LDAP_URL = CONF.ldap.url 
        self.LDAP_USER = CONF.ldap.user 
        self.LDAP_PASSWORD = CONF.ldap.password
        self.suffix = CONF.ldap.suffix
        
        self.user = UserAPI(CONF)
        self.tenant = TenantAPI(CONF)
        self.role = RoleAPI(CONF)
        

    def get_connection(self, user=None, password=None):
        if self.LDAP_URL.startswith('fake://'):
            conn = fakeldap.initialize(self.LDAP_URL)
        else:
            conn = LDAPWrapper(self.LDAP_URL)
        if user is None:
            user = self.LDAP_USER
        if password is None:
            password = self.LDAP_PASSWORD
        conn.simple_bind_s(user, password)
        return conn
    
 
    def get_user(self, user_id):
        user_ref = self._get_user(user_id)
        if (not user_ref):
                return None
        return _filter_user (user_ref)

    def _get_user(self, user_id):
        user_ref = self.user.get(user_id)
        if (not user_ref):
            return None
        tenants = self.tenant.get_user_tenants(user_id)         
        user_ref['tenants'] = []
        for tenant in tenants:
            user_ref['tenants'].append(tenant.id)
        return user_ref


    def authenticate(self, user_id=None, tenant_id=None, password=None):
        """Authenticate based on a user, tenant and password.
        Expects the user object to have a password field and the tenant to be
        in the list of tenants on the user.
        """
        #todo get hostname from config
        
        user_ref = self._get_user(user_id)
        if (user_ref == None):
            raise AssertionError('Invalid user / password')
             
        try:   
            conn = self.user.get_connection(self.user._id_to_dn(user_id), password)
            if (not conn):
                raise AssertionError('Invalid user / password')
        except  Exception as inst:
                raise AssertionError('Invalid user / password')

        if tenant_id:
            found = False
            for tenant in user_ref['tenants']:
                if tenant == tenant_id:
                    found = True
                    break
                
            if (not found):
                raise AssertionError('Invalid tenant')

        #user_ref['tenant_id'] = tenant_id

        tenant_ref = self.tenant.get(tenant_id)
        metadata_ref = {}
        #if tenant_ref:
        #    metadata_ref =  self.get_metadata(user_id, tenant_id)
        #else:
        #    metadata_ref = {}
        return  (_filter_user(user_ref),tenant_ref,metadata_ref)   
        
    def create_user(self, user_id, user):
        return self.user.create(user)
        

    def create_tenant(self, tenant_id, tenant):
        
        data = tenant.copy()
        if 'id' not in data or data['id'] is None:
            data['id'] = str(uuid.uuid4())
        return self.tenant.create(tenant)
        

    def add_user_to_tenant(self, tenant_id, user_id):
        return self.tenant.add_user(tenant_id, user_id)

    def create_role(self, role_id, role):
        return self.role.create(role)

    def get_role(self, role_id):
        return self.role.get(role_id)

    def get_roles_for_user_and_tenant(self, user_id, tenant_id):
        assignments = self.role.get_role_assignments(tenant_id)
        roles =[] 
        for assignment in assignments:
            if assignment.user_id == user_id:
                roles.append(assignment.role_id)        
        return roles
    
    def add_role_for_user_and_tenant(self, user_id, tenant_id, role_id):
        self.role.add_user(role_id, user_id, tenant_id)

    def delete_role(self, role_id):
        return self.role.delete(role_id)

    def get_tenant_by_name(self, tenant_name):
        return self.tenant.get_by_name(tenant_name)

    def get_tenant(self, tenant_id):
        return self.tenant.get(tenant_id)

    def create_metadata(self, user_id, tenant_id, metadata):
        return {}
        
    def get_tenants_for_user(self, user_id):
        tenant_list = []
        for tenant in self.tenant.get_user_tenants(user_id):
            tenant_list.append(tenant.id)
        return tenant_list
        
    def update_user(self, user_id, user):
        return self.user.update(user_id, user)
               
    def update_tenant(self, tenant_id, tenant):
        return self.tenant.update(tenant_id, tenant)

    def get_metadata(self, user_id, tenant_id):
        if (not self.get_tenant(tenant_id)):
            return None
        if (not self.get_user(user_id)):
            return None
        
        metadata_ref = self.get_roles_for_user_and_tenant( user_id, tenant_id)
        return metadata_ref

class UserRoleAssociation():
    """ Role Grant model """

    hints = {
        'contract_attributes': ['id', 'role_id', 'user_id', 'tenant_id'],
        'types': [('user_id', basestring), ('tenant_id', basestring)],
        'maps': {'userId': 'user_id', 'roleId': 'role_id',
                'tenantId': 'tenant_id'}
    }

    def __init__(self, user_id=None, role_id=None, tenant_id=None,
                 *args, **kw):
        # pylint: disable=E0203
        self.user_id=user_id
        self.role_id=role_id
        self.tenant_id=tenant_id
        if isinstance(self.user_id, int):
            # pylint: disable=E0203
            self.user_id = str(self.user_id)
        if isinstance(self.tenant_id, int):
            self.tenant_id = str(self.tenant_id)


# pylint: disable=W0212, W0223
class RoleAPI(BaseLdapAPI):
    DEFAULT_OU = 'ou=Roles'
    DEFAULT_STRUCTURAL_CLASSES = []
    options_name = 'role'
    DEFAULT_OBJECTCLASS = 'organizationalRole'
    DEFAULT_MEMBER_ATTRIBUTE = 'roleOccupant'
    attribute_mapping = {'name': 'cn'}#, 'serviceId': 'service_id'}
    model = models.Tenant


    def __init__(self,conf):
        super(RoleAPI,self).__init__(conf)
        self.user = UserAPI(conf)
        self.tenant = TenantAPI(conf)
        self.member_attribute = getattr(conf.ldap,'role_member_attribute')
        if (self.member_attribute == None):
            self.member_attribute = self.DEFAULT_MEMBER_ATTRIBUTE

    @staticmethod
    def _create_ref(role_id, tenant_id, user_id):
        role_id = '' if role_id is None else str(role_id)
        tenant_id = '' if tenant_id is None else str(tenant_id)
        user_id = '' if user_id is None else str(user_id)
        return '%d-%d-%s%s%s' % (len(role_id), len(tenant_id),
                                 role_id, tenant_id, user_id)

    @staticmethod
    def _explode_ref(rolegrant):
        a = rolegrant.split('-', 2)
        len_role = int(a[0])
        len_tenant = int(a[1])
        role_id = a[2][:len_role]
        role_id = None if len(role_id) == 0 else str(role_id)
        tenant_id = a[2][len_role:len_tenant + len_role]
        tenant_id = None if len(tenant_id) == 0 else str(tenant_id)
        user_id = a[2][len_tenant + len_role:]
        user_id = None if len(user_id) == 0 else str(user_id)
        return role_id, tenant_id, user_id

    def _subrole_id_to_dn(self, role_id, tenant_id):
        if tenant_id is None:
            return self._id_to_dn(role_id)
        else:
            return "cn=%s,%s" % (ldap.dn.escape_dn_chars(role_id),
                                 self.tenant._id_to_dn(tenant_id))

    def get(self, id, filter=None):
        model = super(RoleAPI, self).get(id, filter)
        return model

    def create(self, values):
        #values['id'] = values['name']
        #delattr(values, 'name')

        return super(RoleAPI, self).create(values)

    # pylint: disable=W0221
    def get_by_name(self, name, filter=None):
        return self.get(name, filter)

    def add_user(self, role_id, user_id, tenant_id=None):
        user = self.user.get(user_id)
        if user is None:
            raise Exception("User %s not found" % (user_id,))
        role_dn = self._subrole_id_to_dn(role_id, tenant_id)
        conn = self.get_connection()
        user_dn = self.user._id_to_dn(user_id)
        try:
            conn.modify_s(role_dn, [(ldap.MOD_ADD, 
                                     self.member_attribute, user_dn)])
        except ldap.TYPE_OR_VALUE_EXISTS:
            raise Exception(
                "User %s already has role %s in tenant %s" % (user_id,
                    role_id, tenant_id))
        except ldap.NO_SUCH_OBJECT:
            if tenant_id is None or self.get(role_id) is None:
                raise Exception("Role %s not found" % (role_id,))
            attrs = [
                ('objectClass', [self.object_class]),
                (self.member_attribute, [user_dn]),
            ]
            if self.use_dumb_member:
                attrs[1][1].append(self.DUMB_MEMBER_DN)
            try:
                conn.add_s(role_dn, attrs)
            except Exception as inst:
                    raise inst
        return UserRoleAssociation(
            id=self._create_ref(role_id, tenant_id, user_id),
            role_id=role_id, user_id=user_id, tenant_id=tenant_id)

    def get_by_service(self, service_id):
        roles = self.get_all('(service_id=%s)' % \
                    (ldap.filter.escape_filter_chars(service_id),))
        try:
            res = []
            for role in roles:
                res.append(role)
            return res
        except IndexError:
            return None

    def get_role_assignments(self, tenant_id):
        conn = self.get_connection()
        query = '(objectClass=' +self.object_class+')'
        tenant_dn = self.tenant._id_to_dn(tenant_id)
        try:
            roles = conn.search_s(tenant_dn, ldap.SCOPE_ONELEVEL, query)
        except ldap.NO_SUCH_OBJECT:
            return []
        res = []
        for role_dn, attrs in roles:
            try:
                user_dns = attrs[self.member_attribute]
            except KeyError:
                continue
            for user_dn in user_dns:
                if self.use_dumb_member and user_dn == self.DUMB_MEMBER_DN:
                    continue
                user_id = self.user._dn_to_id(user_dn)
                role_id = self._dn_to_id(role_dn)
                res.append(UserRoleAssociation(
                    id=self._create_ref(role_id, tenant_id, user_id),
                    user_id=user_id,
                    role_id=role_id,
                    tenant_id=tenant_id))
        return res

    def list_global_roles_for_user(self, user_id):
        user_dn = self.user._id_to_dn(user_id)
        roles = self.get_all('(%s=%s)' % (self.member_attribute,user_dn,))
        return [UserRoleAssociation(
                    id=self._create_ref(role.id, None, user_id),
                    role_id=role.id,
                    user_id=user_id) for role in roles]

    def list_tenant_roles_for_user(self, user_id, tenant_id=None):
        conn = self.get_connection()
        user_dn = self.user._id_to_dn(user_id)
        query = '(&(objectClass=%s)(%s=%s))' % (self.object_class,
                                                self.member_attribute,user_dn,)
        if tenant_id is not None:
            tenant_dn = self.tenant._id_to_dn(tenant_id)
            try:
                roles = conn.search_s(tenant_dn, ldap.SCOPE_ONELEVEL, query)
            except ldap.NO_SUCH_OBJECT:
                return []
            res = []
            for role_dn, _ in roles:
                role_id = self._dn_to_id(role_dn)
                res.append(UserRoleAssociation(
                       id=self._create_ref(role_id, tenant_id, user_id),
                       user_id=user_id,
                       role_id=role_id,
                       tenant_id=tenant_id))
            return res
        else:
            try:
                roles = conn.search_s(self.tenant.tree_dn,
                                        ldap.SCOPE_SUBTREE, query)
            except ldap.NO_SUCH_OBJECT:
                return []
            res = []
            for role_dn, _ in roles:
                role_id = self._dn_to_id(role_dn)
                tenant_id = ldap.dn.str2dn(role_dn)[1][0][1]
                res.append(UserRoleAssociation(
                       id=self._create_ref(role_id, tenant_id, user_id),
                       user_id=user_id,
                       role_id=role_id,
                       tenant_id=tenant_id))
            return res

    def rolegrant_get(self, id):
        role_id, tenant_id, user_id = self._explode_ref(id)
        user_dn = self.user._id_to_dn(user_id)
        role_dn = self._subrole_id_to_dn(role_id, tenant_id)
        query = '(&(objectClass=%s)(%s=%s))' % (self.object_class,
                                                self.member_attribute,user_dn,)
        conn = self.get_connection()
        try:
            res = conn.search_s(role_dn, ldap.SCOPE_BASE, query)
        except ldap.NO_SUCH_OBJECT:
            return None
        if len(res) == 0:
            return None
        return UserRoleAssociation(id=id, role_id=role_id,
                                tenant_id=tenant_id, user_id=user_id)

    def rolegrant_delete(self, id):
        role_id, tenant_id, user_id = self._explode_ref(id)
        user_dn = self.user._id_to_dn(user_id)
        role_dn = self._subrole_id_to_dn(role_id, tenant_id)
        conn = self.get_connection()
        try:
            conn.modify_s(role_dn, [(ldap.MOD_DELETE, '', [user_dn])])
        except ldap.NO_SUCH_ATTRIBUTE:
            raise Exception("No such user in role")

    def rolegrant_get_page(self, marker, limit, user_id, tenant_id):
        all_roles = []
        if tenant_id is None:
            all_roles += self.list_global_roles_for_user(user_id)
        else:
            for tenant in self.tenant.get_all():
                all_roles += self.list_tenant_roles_for_user(user_id,
                                                                    tenant.id)
        return self._get_page(marker, limit, all_roles)

    def rolegrant_get_page_markers(self, user_id, tenant_id, marker, limit):
        all_roles = []
        if tenant_id is None:
            all_roles = self.list_global_roles_for_user(user_id)
        else:
            for tenant in self.tenant.get_all():
                all_roles += self.list_tenant_roles_for_user(user_id,
                                                                    tenant.id)
        return self._get_page_markers(marker, limit, all_roles)

    def get_by_service_get_page(self, service_id, marker, limit):
        all_roles = self.get_by_service(service_id)
        return self._get_page(marker, limit, all_roles)

    def get_by_service_get_page_markers(self, service_id, marker, limit):
        all_roles = self.get_by_service(service_id)
        return self._get_page_markers(marker, limit, all_roles)

    def rolegrant_list_by_role(self, id):
        role_dn = self._id_to_dn(id)
        try:
            roles = self.get_all('(%s=%s)' % (self.member_attribute,role_dn,))
        except ldap.NO_SUCH_OBJECT:
            return []
        res = []
        for role_dn, attrs in roles:
            try:
                user_dns = attrs[self.member_attribute]
                tenant_dns = attrs['tenant']
            except KeyError:
                continue
            for user_dn in user_dns:
                if self.use_dumb_member and user_dn == self.DUMB_MEMBER_DN:
                    continue
                user_id = self.user._dn_to_id(user_dn)
                tenant_id = None
                if tenant_dns is not None:
                    for tenant_dn in tenant_dns:
                        tenant_id = self.tenant._dn_to_id(tenant_dn)
                role_id = self._dn_to_id(role_dn)
                res.append(UserRoleAssociation(
                    id=self._create_ref(role_id, tenant_id, user_id),
                    user_id=user_id,
                    role_id=role_id,
                    tenant_id=tenant_id))
        return res

    def rolegrant_get_by_ids(self, user_id, role_id, tenant_id):
        conn = self.get_connection()
        user_dn = self.user._id_to_dn(user_id)
        query = '(&(objectClass=%s)(%s=%s))' % (self.object_class,
                                                self.member_attribute,user_dn)

        if tenant_id is not None:
            tenant_dn = self.tenant._id_to_dn(tenant_id)
            try:
                roles = conn.search_s(tenant_dn, ldap.SCOPE_ONELEVEL, query)
            except ldap.NO_SUCH_OBJECT:
                return None
            if len(roles) == 0:
                return None
            for role_dn, _ in roles:
                ldap_role_id = self._dn_to_id(role_dn)
                if role_id == ldap_role_id:
                    res = UserRoleAssociation(
                           id=self._create_ref(role_id, tenant_id, user_id),
                           user_id=user_id,
                           role_id=role_id,
                           tenant_id=tenant_id)
                    return res
        else:
            try:
                roles = self.get_all('(%s=%s)' % (self.member_attribute,
                                                  user_dn,))
            except ldap.NO_SUCH_OBJECT:
                return None
            if len(roles) == 0:
                return None
            for role in roles:
                if role.id == role_id:
                    return UserRoleAssociation(
                                id=self._create_ref(role.id, None, user_id),
                                role_id=role.id,
                                user_id=user_id)
        return None

        
class TenantAPI(BaseLdapAPI):  # pylint: disable=W0223
    DEFAULT_OU = 'ou=Groups'
    DEFAULT_STRUCTURAL_CLASSES = []
    DEFAULT_OBJECTCLASS = 'groupOfNames'
    DEFAULT_ID_ATTRIBUTE = 'cn'
    DEFAULT_MEMBER_ATTRIBUTE ='member'
    options_name = 'tenant'
    attribute_mapping = {
                         #'description': 'desc', 'enabled': 'keystoneEnabled',
                         'name': 'ou'}
    model = models.Tenant

    def __init__(self,conf):
        super(TenantAPI,self).__init__(conf)
        self.user = UserAPI(conf)
        self.member_attribute = getattr(conf.ldap,'tenant_member_attribute')
        if (self.member_attribute == None):
            self.member_attribute = self.DEFAULT_MEMBER_ATTRIBUTE
        
    def get_by_name(self, name, filter=None):  # pylint: disable=W0221,W0613
        search_filter = '(%s=%s)' % \
                            (self.attribute_mapping['name'], ldap.filter.escape_filter_chars(name),)
        tenants = self.get_all(search_filter)
        try:
            return tenants[0]
        except IndexError:
            return None

    def create(self, values):
        self.affirm_unique(values)

        data = values.copy()
        if 'id' not in data or data['id'] is None:
            data['id'] = str(uuid.uuid4())
        return super(TenantAPI, self).create(data)

    def get_user_tenants(self, user_id):
        """Returns list of tenants a user has access to

        Always includes default tenants.
        """
        user_dn = self.user._id_to_dn(user_id)  # pylint: disable=W0212
        query = '(%s=%s)' % (self.member_attribute,user_dn,)
        memberships = self.get_all(query)
        return memberships

    def xxxget_user_tenants(self, user_id, include_roles=True):
        """Returns list of tenants a user has access to

        Always includes default tenants.
        Adds role assignments if 'include_roles' is True.
        """
        user_dn = self.user._id_to_dn(user_id)  # pylint: disable=W0212
        query = '(%s=%s)' % (self.member_attribute,user_dn,)
        memberships = self.get_all(query)
        if include_roles:
            roles = self.role.list_tenant_roles_for_user(user_id)
            for role in roles:
                exists = False
                for tenant in memberships:
                    if tenant['id'] == role.tenant_id:
                        exists = True
                        break
                if not exists:
                    memberships.append(self.get(role.tenant_id))
        return memberships


    def list_for_user_get_page(self, user, marker, limit):
        return self._get_page(marker, limit, self.get_user_tenants(user.id))

    def list_for_user_get_page_markers(self, user, marker, limit):
        return self._get_page_markers(marker, limit,
                        self.get_user_tenants(user.id))

    def is_empty(self, id):
        tenant = self._ldap_get(id)
        members = tenant[1].get(self.member_attribute, [])
        if self.use_dumb_member:
            empty = members == [self.DUMB_MEMBER_DN]
        else:
            empty = len(members) == 0
        return empty and len(self.api.role.get_role_assignments(id)) == 0

    def get_role_assignments(self, tenant_id):
        return self.api.role.get_role_assignments(tenant_id)

    def add_user(self, tenant_id, user_id):
        conn = self.get_connection()
        conn.modify_s(self._id_to_dn(tenant_id),
            [(ldap.MOD_ADD, self.member_attribute,
              self.user._id_to_dn(user_id))])  # pylint: disable=W0212

    def remove_user(self, tenant_id, user_id):
        conn = self.get_connection()
        conn.modify_s(self._id_to_dn(tenant_id),
            [(ldap.MOD_DELETE, self.member_attribute,
              self.user._id_to_dn(user_id))])  # pylint: disable=W0212

    def get_users(self, tenant_id, role_id=None):
        tenant = self._ldap_get(tenant_id)
        res = []
        if not role_id:
            # Get users who have default tenant mapping
            for user_dn in tenant[1].get(self.member_attribute, []):
                if self.use_dumb_member and user_dn == self.DUMB_MEMBER_DN:
                    continue
                #pylint: disable=W0212
                res.append(self.user.get(self.user._dn_to_id(user_dn)))
        rolegrants = self.api.role.get_role_assignments(tenant_id)
        # Get users who are explicitly mapped via a tenant
        for rolegrant in rolegrants:
            if role_id is None or rolegrant.role_id == role_id:
                res.append(self.user.get(rolegrant.user_id))
        return res

    def delete(self, id):
        super(TenantAPI, self).delete(id)

    def update(self, id, values):
        old_obj = self.get(id)
        if old_obj.name != values['name']:
            raise "Changing Name not permitted"
        super(TenantAPI, self).update(id, values,old_obj)


def _ensure_hashed_password(user_ref):
    pw = user_ref.get('password', None)
    if pw is not None:
        pw = utils.ldap_hash_password(pw)
        user_ref['password'] = pw
    return user_ref

class UserAPI(BaseLdapAPI):
    DEFAULT_OU = 'ou=Users'
    DEFAULT_STRUCTURAL_CLASSES = ['person']
    DEFAULT_ID_ATTRIBUTE = 'cn'
    DEFAULT_OBJECTCLASS='inetOrgPerson'
    options_name = 'user'
    attribute_mapping = {
        'password': 'userPassword',
        #'email': 'mail',
        'name': 'sn',
    }
    #The RFC based schemas don't have a way to indicate 'enabled'
    #the closest is the nsAccount lock,  which is on definied to
    # be part of any objectclass
    # in the future, we need to provide a way for the end user to
    #indicate the field to use and what it indicates
    attribute_ignore = ['tenant_id','enabled','tenants']
    model = models.User

    def get_by_name(self, name, filter=None):
        users = self.get_all('(%s=%s)' % \
                            (self.attribute_mapping['name'],
                             ldap.filter.escape_filter_chars(name),))
        try:
            return users[0]
        except IndexError:
            return None


    def create(self, values):
        self.affirm_unique( values)
        #values['id'] = str(uuid.uuid4())
        _ensure_hashed_password(values)
        values = super(UserAPI, self).create(values)
        tenant_id= values.get('tenant_id')
        if tenant_id is not None:
            self.api.tenant.add_user(values['tenant_id'], values['id'])
        return values

    def update(self, id, values):
        if (values['id'] != id):
            return None
        old_obj = self.get(id)
        if old_obj.name != values['name']:
            raise "Changing Name not permitted"
        try:
            new_tenant = values['tenant_id']
        except KeyError:
            pass
        else:
            if old_obj.tenant_id != new_tenant:
                if old_obj.tenant_id:
                    self.api.tenant.remove_user(old_obj.tenant_id, id)
                if new_tenant:
                    self.api.tenant.add_user(new_tenant, id)
        _ensure_hashed_password(values)
        super(UserAPI, self).update(id, values, old_obj)

    def delete(self, id):
        user = self.get(id)
        if user.tenant_id:
            self.api.tenant.remove_user(user.tenant_id, id)
        super(UserAPI, self).delete(id)
        for ref in self.api.role.list_global_roles_for_user(id):
            self.api.role.rolegrant_delete(ref.id)
        for ref in self.api.role.list_tenant_roles_for_user(id):
            self.api.role.rolegrant_delete(ref.id)

    def get_by_email(self, email):
        users = self.get_all('(mail=%s)' % \
                            (ldap.filter.escape_filter_chars(email),))
        try:
            return users[0]
        except IndexError:
            return None

    def user_roles_by_tenant(self, user_id, tenant_id):
        return self.api.role.list_tenant_roles_for_user(user_id, tenant_id)

    def get_by_tenant(self, user_id, tenant_id):
        user_dn = self._id_to_dn(user_id)
        user = self.get(user_id)
        tenant = self.api.tenant._ldap_get(tenant_id,
                                           '(member=%s)' % (user_dn,))
        if tenant is not None:
            return user
        else:
            if self.api.role.list_tenant_roles_for_user(user_id, tenant_id):
                return user
        return None

    def user_role_add(self, values):
        return self.api.role.add_user(values.role_id, values.user_id,
                                      values.tenant_id)

    def users_get_page(self, marker, limit):
        return self.get_page(marker, limit)

    def users_get_page_markers(self, marker, limit):
        return self.get_page_markers(marker, limit)

    def users_get_by_tenant_get_page(self, tenant_id, role_id, marker, limit):
        return self._get_page(marker, limit,
                self.api.tenant.get_users(tenant_id, role_id))

    def users_get_by_tenant_get_page_markers(self, tenant_id,
        role_id, marker, limit):
        return self._get_page_markers(marker, limit,
                self.api.tenant.get_users(tenant_id, role_id))

    def check_password(self, user_id, password):
        user = self.get(user_id)
        return utils.check_password(password, user.password)


        