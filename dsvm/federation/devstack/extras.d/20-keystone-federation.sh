# Keystone devstack plugin for federation

if is_service_enabled key; then

    if [[ "$1" == "source" ]]; then
        source $TOP_DIR/lib/keystone-federation
    fi

    if [[ "$1" == "stack" && "$2" == "pre-install" ]]; then
        # no-op
        :

    elif [[ "$1" == "stack" && "$2" == "install" ]]; then
        # Called after Keystone is installed
        echo_summary "Installing Keystone Federation"
        # NOTE(dstanek): we probably want to make this configurable later
        install_keystone_federation

        echo_summary "Configuring Keystone Federation"
        configure_keystone_federation

    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        # Called after Keystone configuration
        init_keystone_federation

    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        # Keystone has been started so let's start federation
        echo_summary "Starting Keystone Federation"
        start_keystone_federation
    fi

    if [[ "$1" == "unstack" ]]; then
        echo_summary "Stopping Keystone Federation"
        stop_keystone_federation
    fi

    if [[ "$1" == "clean" ]]; then
        # Remove state and transient data
        # Remember clean.sh first calls unstack.sh
        # no-op
        :
    fi
fi
