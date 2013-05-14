import json

from keystone.common import cms
from keystone.common import controller
from keystone.common import dependency
from keystone.common import logging
from keystone import config
from keystone import exception
from keystone.openstack.common import timeutils

CONF = config.CONF
LOG = logging.getLogger(__name__)
DEFAULT_DOMAIN_ID = CONF.identity.default_domain_id


class ExternalAuthNotApplicable(Exception):
    """External authentication is not applicable"""
    pass


@dependency.requires('catalog_api', 'trust_api', 'token_api',
                     'token_provider_api')
class Auth(controller.V2Controller):
    def ca_cert(self, context, auth=None):
        ca_file = open(CONF.signing.ca_certs, 'r')
        data = ca_file.read()
        ca_file.close()
        return data

    def signing_cert(self, context, auth=None):
        cert_file = open(CONF.signing.certfile, 'r')
        data = cert_file.read()
        cert_file.close()
        return data

    def _get_v3_token_auth(self, context, auth):
        if 'token' not in auth:
            raise exception.ValidationError(
                attribute='token', target='auth')

        if "id" not in auth['token']:
            raise exception.ValidationError(
                attribute="id", target="token")

        v3_auth = {'identity': {'methods': ['token'],
                                'token': {'id': auth['token']['id']}}}
        if 'trust_id' in auth:
            v3_auth['scope'] = {'OS-TRUST:trust': {'id': auth['trust_id']}}
        else:
            tenant_id = self._get_project_id_from_auth(context, auth)
            if tenant_id:
                v3_auth['scope'] = {'project': {'id': tenant_id}}
        return v3_auth

    def _get_v3_password_auth(self, context, auth):
        if "password" not in auth['passwordCredentials']:
            raise exception.ValidationError(
                attribute='password', target='passwordCredentials')
        password = auth['passwordCredentials']['password']
        if ("userId" not in auth['passwordCredentials'] and
                "username" not in auth['passwordCredentials']):
            raise exception.ValidationError(
                attribute='username or userId',
                target='passwordCredentials')
        user_id = auth['passwordCredentials'].get('userId')
        username = auth['passwordCredentials'].get('username')
        v3_auth = {'identity': {'methods': ['password'],
                                'password': {}}}
        if user_id:
            v3_auth['identity']['password']['user'] = {'id': user_id,
                                                       'password': password}
        else:
            v3_auth['identity']['password']['user'] = {'name': username,
                                                       'password': password,
                                                       'domain': {'id':
                                                       DEFAULT_DOMAIN_ID}}
        tenant_id = self._get_project_id_from_auth(context, auth)
        if tenant_id:
            v3_auth['scope'] = {'project': {'id': tenant_id}}
        return v3_auth

    def _get_v3_remote_user_auth(self, context, auth):
        username = context['REMOTE_USER']
        tenant_id = self._get_project_id_from_auth(context, auth)
        v3_auth = {'identity': {'methods': ['password'],
                                'password': {'user': {'name': username,
                                                      'domain': {'id':
                                                      DEFAULT_DOMAIN_ID}}}}}
        if tenant_id:
            v3_auth['scope'] = {'project': {'id': tenant_id}}
        return v3_auth

    def _get_v3_auth(self, context, auth):
        """Translate v2 auth into v3 auth."""
        #FIXME(gyee): should it be done at middleware?
        if auth is None:
            raise exception.ValidationError(attribute='auth',
                                            target='request body')
        if 'token' in auth:
            return self._get_v3_token_auth(context, auth)
        elif 'passwordCredentials' in auth:
            return self._get_v3_password_auth(context, auth)
        elif 'REMOTE_USER' in context:
            return self._get_v3_remote_user_auth(context, auth)
        else:
            raise exception.ValidationError(attribute='auth', target='auth')

    def authenticate(self, context, auth=None):
        """Authenticate credentials and return a token.

        Accept auth as a dict that looks like::

            {
                "auth":{
                    "passwordCredentials":{
                        "username":"test_user",
                        "password":"mypass"
                    },
                    "tenantName":"customer-x"
                }
            }

        In this case, tenant is optional, if not provided the token will be
        considered "unscoped" and can later be used to get a scoped token.

        Alternatively, this call accepts auth with only a token and tenant
        that will return a token that is scoped to that tenant.
        """
        v3_auth_data = self._get_v3_auth(context, auth)

        # do lazy loading here because of circular dependency
        from keystone.auth import controllers as v3_auth_controller
        V3_AUTH = v3_auth_controller.Auth()
        (token_id, token_data) = V3_AUTH.authenticate_for_token_data(
            context, v3_auth_data)

        #FIXME(gyee): provider issues v3 token so we have to set to ID here
        # so the v2 token middleware can translate this correctly
        token_data['token']['id'] = token_id

        return token_data

    def _get_project_id_from_auth(self, context, auth):
        """Extract tenant information from auth dict.

        Returns a valid tenant_id if it exists, or None if not specified.
        """
        tenant_id = auth.get('tenantId', None)
        if tenant_id and len(tenant_id) > CONF.max_param_size:
            raise exception.ValidationSizeError(attribute='tenantId',
                                                size=CONF.max_param_size)

        tenant_name = auth.get('tenantName', None)
        if tenant_name and len(tenant_name) > CONF.max_param_size:
            raise exception.ValidationSizeError(attribute='tenantName',
                                                size=CONF.max_param_size)

        if tenant_name:
            try:
                tenant_ref = self.identity_api.get_project_by_name(
                    context=context, tenant_name=tenant_name,
                    domain_id=DEFAULT_DOMAIN_ID)
                tenant_id = tenant_ref['id']
            except exception.ProjectNotFound as e:
                raise exception.Unauthorized(e)
        return tenant_id

    def _get_token_ref(self, context, token_id, belongs_to=None):
        """Returns a token if a valid one exists.

        Optionally, limited to a token owned by a specific tenant.

        """
        # TODO(termie): this stuff should probably be moved to middleware
        self.assert_admin(context)
        data = self.token_api.get_token(context=context,
                                        token_id=token_id)
        if belongs_to:
            if data.get('tenant') is None:
                raise exception.Unauthorized(
                    _('Token does not belong to specified tenant.'))
            if data['tenant'].get('id') != belongs_to:
                raise exception.Unauthorized(
                    _('Token does not belong to specified tenant.'))
        return data

    # admin only
    def validate_token_head(self, context, token_id):
        """Check that a token is valid.

        Optionally, also ensure that it is owned by a specific tenant.

        Identical to ``validate_token``, except does not return a response.

        """
        self.assert_admin(context)
        belongs_to = context['query_string'].get('belongsTo')
        self.token_provider_api.check_token(
            context,
            token_id,
            belongs_to,
            belongs_to_domain=DEFAULT_DOMAIN_ID,
            no_domain_scope=True)

    # admin only
    def validate_token(self, context, token_id):
        """Check that a token is valid.

        Optionally, also ensure that it is owned by a specific tenant.

        Returns metadata about the token along any associated roles.

        """
        self.assert_admin(context)
        belongs_to = context['query_string'].get('belongsTo')
        token_data = self.token_provider_api.validate_token(
            context,
            token_id=token_id,
            belongs_to=belongs_to,
            belongs_to_domain=DEFAULT_DOMAIN_ID,
            no_domain_scope=True)
        #FIXME(gyee): provider issues v3 token so we have to set to ID here
        # so the v2 token middleware can translate this correctly
        token_data['token']['id'] = token_id

        return token_data

    def delete_token(self, context, token_id):
        """Delete a token, effectively invalidating it for authz."""
        # TODO(termie): this stuff should probably be moved to middleware
        self.assert_admin(context)
        self.token_provider_api.revoke_token(
            context=context, token_id=token_id)

    def revocation_list(self, context, auth=None):
        self.assert_admin(context)
        tokens = self.token_api.list_revoked_tokens(context)

        for t in tokens:
            expires = t['expires']
            if not (expires and isinstance(expires, unicode)):
                    t['expires'] = timeutils.isotime(expires)
        data = {'revoked': tokens}
        json_data = json.dumps(data)
        signed_text = cms.cms_sign_text(json_data,
                                        CONF.signing.certfile,
                                        CONF.signing.keyfile)

        return {'signed': signed_text}

    def endpoints(self, context, token_id):
        """Return a list of endpoints available to the token."""
        self.assert_admin(context)

        token_ref = self._get_token_ref(context, token_id)

        catalog_ref = None
        if token_ref.get('tenant'):
            catalog_ref = self.catalog_api.get_catalog(
                context=context,
                user_id=token_ref['user']['id'],
                tenant_id=token_ref['tenant']['id'],
                metadata=token_ref['metadata'])

        return Auth.format_endpoint_list(catalog_ref)

    @classmethod
    def format_endpoint_list(cls, catalog_ref):
        """Formats a list of endpoints according to Identity API v2.

        The v2.0 API wants an endpoint list to look like::

            {
                'endpoints': [
                    {
                        'id': $endpoint_id,
                        'name': $SERVICE[name],
                        'type': $SERVICE,
                        'tenantId': $tenant_id,
                        'region': $REGION,
                    }
                ],
                'endpoints_links': [],
            }

        """
        if not catalog_ref:
            return {}

        endpoints = []
        for region_name, region_ref in catalog_ref.iteritems():
            for service_type, service_ref in region_ref.iteritems():
                endpoints.append({
                    'id': service_ref.get('id'),
                    'name': service_ref.get('name'),
                    'type': service_type,
                    'region': region_name,
                    'publicURL': service_ref.get('publicURL'),
                    'internalURL': service_ref.get('internalURL'),
                    'adminURL': service_ref.get('adminURL'),
                })

        return {'endpoints': endpoints, 'endpoints_links': []}
