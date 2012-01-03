from keystone import version
from keystone.manage2 import common


@common.arg('--api', action='store_true',
    default=False,
    help='only print the API version')
@common.arg('--implementation', action='store_true',
    default=False,
    help='only print the implementation version')
class Command(common.BaseCommand):
    """Returns keystone version data.

    Includes the latest API version, implementation version, or both,
    if neither is specified.
    """

    @staticmethod
    def get_api_version():
        """Returns a complete API version string"""
        return ' '.join([version.API_VERSION, version.API_VERSION_STATUS])

    @staticmethod
    def get_implementation_version():
        """Returns a complete implementation version string"""
        return version.version()

    def run(self, args):
        """Process argparse args, and print results to stdout"""
        show_all = not (args.api or args.implementation)

        if args.api or show_all:
            print 'API v%s' % Command.get_api_version()
        if args.implementation or show_all:
            print 'Implementation v%s' % Command.get_implementation_version()
