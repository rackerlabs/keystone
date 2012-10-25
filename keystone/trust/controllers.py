import uuid
import json

from keystone import config
from keystone.common import cms
from keystone.common import controller
from keystone.common import dependency
from keystone.common import logging
from keystone import exception
from keystone.openstack.common import timeutils


LOG = logging.getLogger(__name__)


@dependency.requires('identity_api', 'trust_api')
class Trust(controller.V3Controller):

    def create_trust(self, context, body):
        """
        Do not validate the values of the trust now:
        trust data is validated when the tokens are created.
        These values might not be valid yet, but may be in the future
        The one exception is that the user creating the trust
        must be trustor
        TODO enforce this last rule
        """
        trust_request = body['trust']

        return self.trust_api.create_trust(
            context=context,
            trust_id=uuid.uuid4().hex,
            trustor=trust_request['trustor'],
            trustee=trust_request['trustee'],
            tenant=trust_request['tenant'],
            roles=trust_request['roles'],
            endpoints=trust_request['endpoints'])

    def list_trusts(self, context):
        return {'trust': '123456'}

    def delete_trust(self, context, trust_to_delete):
        return {}
