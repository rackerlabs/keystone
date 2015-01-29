# Devstack extras script to install a pysaml2 IdP

if is_service_enabled k-pyidp; then
    if [[ "$1" == "source" ]]; then
        source $TOP_DIR/lib/pysaml2_idp
    elif [[ "$1" == "stack" && "$2" == "install" ]]; then
        echo_summary "Installing pysaml2 IdP"
        install_pysaml2_idp
    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        echo_summary "Configuring pysaml2 IdP"
        configure_pysaml2_idp
    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        echo_summary "Starting pysaml2 IdP"
        start_pysaml2_idp
    fi

    if [[ "$1" == "unstack" ]]; then
        stop_pysaml2_idp
    fi
fi
