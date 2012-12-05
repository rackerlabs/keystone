from keystone.policy import controllers
from keystone.routers import crud


def V3_routers(mapper, routers):
    policy_controller = controllers.PolicyV3()
    routers.append(crud.Router(policy_controller, 'policies', 'policy'))
