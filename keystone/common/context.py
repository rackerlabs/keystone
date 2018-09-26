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

from oslo_context import context as oslo_context


REQUEST_CONTEXT_ENV = 'keystone.oslo_request_context'


def _prop(name):
    return property(lambda x: getattr(x, name),
                    lambda x, y: setattr(x, name, y))


class RequestContext(oslo_context.RequestContext):

    def __init__(self, **kwargs):
        self.user_id = kwargs.pop('user_id ', None)
        self.project_id = kwargs.pop('project_id ', None)
        self.domain_id = kwargs.pop('domain_id ', None)
        self.user_domain_id = kwargs.pop('user_domain_id ', None)
        self.project_domain_id = kwargs.pop('project_domain_id ', None)

        self.project_name = kwargs.pop('project_name', None)
        self.domain_name = kwargs.pop('domain_name', None)
        self.username = kwargs.pop('username', None)
        self.user_domain_name = kwargs.pop('user_domain_name', None)
        self.project_domain_name = kwargs.pop('project_domain_name', None)
        self.project_tag_name = kwargs.pop('project_tag_name', None)

        self.is_delegated_auth = kwargs.pop('is_delegated_auth', False)

        self.trust_id = kwargs.pop('trust_id', None)
        self.trustor_id = kwargs.pop('trustor_id', None)
        self.trustee_id = kwargs.pop('trustee_id', None)

        self.oauth_consumer_id = kwargs.pop('oauth_consumer_id', None)
        self.oauth_access_token_id = kwargs.pop('oauth_access_token_id', None)

        self.authenticated = kwargs.pop('authenticated', False)
        super(RequestContext, self).__init__(**kwargs)

    @classmethod
    def from_environ(cls, environ, **kwargs):
        kwargs.setdefault('request_id', environ.get('openstack.request_id'))
        return super(RequestContext, cls).from_environ(environ, **kwargs)

    def to_policy_values(self):
        """Add keystone-specific policy values to policy reprensetation.

        This method converts generic policy values to a dictionary form using
        the base implementation from oslo_context.context.RequestContext.
        Afterwords it is going to pull keystone-specific values off the context
        and represent them as items in the policy values dictionary. This is
        because keystone uses default policies that rely on these values, so we
        need to gaurantee they are present during policy enforcement if they
        are present on the context object.

        This method is automatically called in
        oslo_policy.policy.Enforcer.enforce() if oslo.policy knows it's dealing
        with a context object.

        """
        # TODO(morgan): Rework this to not need an explicit token render as
        # this is a generally poorly designed behavior. The enforcer should not
        # rely on a contract of the token's rendered JSON form. This likely
        # needs reworking of how we handle the context in oslo.policy. Until
        # this is reworked, it is not possible to merge the token render
        # function into keystone.api
        values = super(RequestContext, self).to_policy_values()
        values['token'] = self.token_reference['token']
        values['domain_id'] = self.domain_id if self.domain_id else None
        return values
