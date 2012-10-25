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

    def create(self, context, trust):
        """
        Do not validate the values of the trust now:
        trust data is validated when the tokens are created.
        These values might not be valid yet, but may be in the future
        The one exception is that the user creating the trust
        must be trustor
        TODO enforce this last rule
        """
        user_id = self._get_user_id(context)
        if user_id != trust['trustor']:
            raise exception.ForbiddenAction()

        new_trust = self.trust_api.create_trust(
            context=context,
            trust_id=uuid.uuid4().hex,
            trustor=trust['trustor'],
            trustee=trust['trustee'],
            project=trust['project'],
            roles=trust['roles'],
            endpoints=trust['endpoints'])

        return {'trust': new_trust}

    def list_trusts_for_trustee(self, trustee):
        return self.trust_api.list_trusts_for_trustee(context, trustee)

    def list_trusts_for_trustor(self, trustor):
        return self.trust_api.list_trusts_for_trustor(context, trustor)

    def delete(self, context, trust_id):
        trust = self.trust_api.get_trust(context, trust_id)
        self.trust_api.delete_trust(context, trust_id)
        userid = trust['trustor']
        token_list = self.token_api.list_tokens(context,
                                                userid,
                                                trust_id=trust_id)
        for token in token_list:
            self.token_api.delete_token(context, token)
