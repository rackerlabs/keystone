"""Prints keystone's version information"""


from keystone import version
from keystone.manage2 import common


@common.arg('--api', action='store_true',
    default=False,
    help='only print the API version')
@common.arg('--implementation', action='store_true',
    default=False,
    help='only print the implementation version')
class Command(common.BaseCommand):
    def get_api_version(self):
        return ' '.join([version.API_VERSION, version.API_VERSION_STATUS])

    def get_implementation_version(self):
        return version.version()

    @staticmethod
    def run(args):
        cmd = Command()

        show_all = not (args.api or args.implementation)

        if args.api or show_all:
            print 'API v%s' % cmd.get_api_version()
        if args.implementation or show_all:
            print 'Implementation v%s' % cmd.get_implementation_version()
