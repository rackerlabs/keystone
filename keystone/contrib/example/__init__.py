from keystone.contrib.example import controllers
from keystone.openstack.common.notifier import extensions_notifier

controller = controllers.ExampleV3Controller()

subscribed_events = {
    'identity.project.deleted': controller.project_deleted_notification,
    'identity.project.created': controller.project_created_notification
}

extensions_notifier.register(subscribed_events)
