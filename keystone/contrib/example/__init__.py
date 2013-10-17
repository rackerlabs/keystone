from keystone.contrib.example import controllers
from keystone.openstack.common.notifier import extensions_notifier

subscribed_events = {
    'identity.project.deleted': controllers.ExampleV3Controller().projectDeleted,
    'identity.project.created': controllers.ExampleV3Controller().projectCreated
}

extensions_notifier.register(subscribed_events)
