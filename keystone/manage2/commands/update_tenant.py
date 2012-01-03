from keystone.manage2 import common


@common.arg('--where-id',
    required=True,
    help='identifies the tenant to update by ID')
@common.arg('--name',
    required=False,
    help="change the tenant's name")
@common.arg('--enable',
    action='store_true',
    required=False,
    default=None,
    help="enable the tenant")
@common.arg('--disable',
    action='store_true',
    required=False,
    default=None,
    help="disable the tenant")
class Command(common.BaseBackendCommand):
    """Updates the specified tenant."""

    def update_tenant(self, id, name=None, enabled=None):
        tenant = self.get_tenant(id)

        if name is not None:
            tenant.name = name

        if enabled is not None:
            tenant.enabled = enabled

        self.tenant_manager.update(tenant)

    def run(self, args):
        """Process argparse args, and print results to stdout"""
        enabled = None
        if args.enable and args.disable:
            args.error("You can't both --enable and --disable a tenant")
        elif args.disable:
            enabled = False
        elif args.enable:
            enabled = True

        self.update_tenant(id=args.where_id, name=args.name, enabled=enabled)
