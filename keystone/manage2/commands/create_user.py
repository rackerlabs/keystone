from keystone.manage2 import common
from keystone.backends import models


@common.arg('--id',
    required=False,
    help='a unique identifier used in URLs')
@common.arg('--name',
    required=True,
    help='a unique username used for authentication')
@common.arg('--email',
    required=False,
    help='a unique email address')
@common.arg('--password',
    required=True,
    help='used for authentication')
@common.arg('--tenant-id',
    required=False,
    help='default tenant ID')
@common.arg('--disabled',
    action='store_true',
    required=False,
    default=False,
    help="create the user in a disabled state (users are enabled by "
            "default)")
class Command(common.BaseBackendCommand):
    """Creates a new user, enabled by default.

    Optionally, specify a default tenant for the user.
    The user is enabled by default, but can be disabled upon creation as
    well.
    """

    def create_user(self, name, password, id=None, email=None, tenant_id=None,
            enabled=True):
        if tenant_id is not None:
            self.tenant_manager.get(tenant_id)

        obj = models.User()
        obj.id = id
        obj.name = name
        obj.password = password
        obj.email = email
        obj.enabled = enabled
        obj.tenant_id = tenant_id

        user = self.user_manager.create(obj)
        return user

    def run(self, args):
        """Process argparse args, and print results to stdout"""
        user = self.create_user(id=args.id, name=args.name,
                password=args.password, email=args.email,
                tenant_id=args.tenant_id, enabled=(not args.disabled))
        print user.id
