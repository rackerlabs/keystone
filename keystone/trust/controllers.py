import uuid
import json

from keystone import config
from keystone import exception
from keystone.common import controller
from keystone.common import dependency
from keystone.common import logging
from keystone import exception
from keystone.openstack.common import timeutils


LOG = logging.getLogger(__name__)


@dependency.requires('identity_api', 'trust_api', 'token_api')
class Trust(controller.V3Controller):

    def _get_user_id(self, context):
        if 'token_id' in context:
            token_id = context['token_id']
            token = self.token_api.get_token(context, token_id)
            user_id = token['user']['id']
            return user_id
        return None

    def get_trust(self, context, trust_id):
        user_id = self._get_user_id(context)
        try:
            trust = self.trust_api.get_trust(trust_id)
            if (user_id != trust['trustor_user_id'] or
                    user_id != trust['trustee_user_id']):
                raise exception.ForbiddenAction()
        except Exception:
            raise exception.ForbiddenAction()

    @controller.protected
    def create_trust(self, context, trust):
        """
        Do not validate the values of the trust now:
        trust data is validated when the tokens are created.
        These values might not be valid yet, but may be in the future
        The one exception is that the user creating the trust
        must be trustor
        """
        user_id = self._get_user_id(context)
        if user_id != trust['trustor_user_id']:
            raise exception.ForbiddenAction()

        #TODO" ayoung  confirm the values prior to creating the trust
        new_trust = self.trust_api.create_trust(
            context=context,
            trust_id=uuid.uuid4().hex,
            trustor_user_id=trust['trustor_user_id'],
            trustee_user_id=trust['trustee_user_id'],
            project=trust['project'],
            roles=trust['roles'],
            endpoints=trust['endpoints'])

        return {'trust': new_trust}

#    @controller.protected
    def list_trusts_for_user(self, context, user_id):
        query = context['query_string']
        calling_user_id = self._get_user_id(context)
        if user_id != calling_user_id:
            raise exception.ForbiddenAction()
        trusts = {}
        if not query or 'as_trustor' in query:
            trusts["as_trustor"] = (self.trust_api.
                                    list_trusts_for_trustor(context, user_id))

        if not query or 'as_trustee' in query:
            trusts["as_trustee"] = (self.trust_api.
                                    list_trusts_for_trustee(context, user_id))
        return trusts

    @controller.protected
    def list_trusts(self, context):
        self.assert_admin(context)
        trusts = self.trust_api.list_trusts(context)
        return {"trusts": trusts}

    @controller.protected
    def delete_trust(self, context, trust_id):
        trust = self.trust_api.get_trust(context, trust_id)
        self.trust_api.delete_trust(context, trust_id)
        userid = trust['trustor_user_id']
        token_list = self.token_api.list_tokens(context,
                                                userid,
                                                trust_id=trust_id)
        for token in token_list:
            self.token_api.delete_token(context, token)
