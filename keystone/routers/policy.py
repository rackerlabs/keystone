from keystone import policy
from keystone.routers import crud


def V3_routers(mapper, routers):
    policy_controller = policy.controllers.PolicyV3()
    routers.append(crud.Router(policy_controller, 'policies', 'policy'))
