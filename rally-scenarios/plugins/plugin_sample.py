
"""
For more keystone related benchmarks take a look here:
github.com/stackforge/rally/blob/master/rally/benchmark/scenarios/keystone/

About plugins: https://rally.readthedocs.org/en/latest/plugins.html

Rally concepts https://wiki.openstack.org/wiki/Rally/Concepts
"""


from rally.benchmark.scenarios import base
from rally.benchmark.scenarios import utils as scenario_utils


class KeystonePlugin(base.Scenario):

    @scenario_utils.atomic_action_timer("create_user_label")
    def _create_user(self, name_length=10):
        name = self._generate_random_name(length=name_length)
        password = name
        email = name + "@rally.me"
        return self.admin_clients("keystone").users.create(name, password,
                                                           email)

    @scenario_utils.atomic_action_timer("delete_user_label")
    def _delete_user(self, user):
        user.delete()

    @base.scenario(admin_only=True)
    def your_mega_benchmark(self, name_length=10):
        user = self._create_user(name_length)
        self._delete_user(user)
