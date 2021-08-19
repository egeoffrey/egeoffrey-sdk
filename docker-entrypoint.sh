#!/bin/sh

# variables
SUPPORTED_MANIFEST_SCHEMA=2
PACKAGE_MANIFEST="manifest.yml"
SDK_MANIFEST="sdk/manifest.yml"

# extract a string value from a file
extract()
{
    STRING=$1
    FILE=$2
    grep "^$STRING:" $FILE | awk '{ print $2}'
}

# extract relevant information from the manifest
LANGUAGE="python"
if [ -f "$PACKAGE_MANIFEST" ]; then
    # Get the package manifest schema version if the file exists
    MANIFEST_SCHEMA=$(extract manifest_schema $PACKAGE_MANIFEST)
    if [ $MANIFEST_SCHEMA != $SUPPORTED_MANIFEST_SCHEMA ]; then
        echo "ERROR: unsupported manifest schema v"$MANIFEST_SCHEMA
        exit
    fi
    # Get the runtime language to use
    PACKAGE_LANGUAGE=$(extract language $PACKAGE_MANIFEST)
    if [ -n "$PACKAGE_LANGUAGE" ]; then
        LANGUAGE=$PACKAGE_LANGUAGE
    fi
fi

# welcome message (package)
if [ -f "$PACKAGE_MANIFEST" ]; then
    echo -e "Package "$(extract package $PACKAGE_MANIFEST)" v"$(extract version $PACKAGE_MANIFEST |xargs printf '%.1f')"-"$(extract revision $PACKAGE_MANIFEST)" ("$(extract branch $PACKAGE_MANIFEST)") ["$LANGUAGE"] | SDK v"$(extract version $SDK_MANIFEST |xargs printf '%.1f')"-"$(extract revision $SDK_MANIFEST)" ("$(extract branch $SDK_MANIFEST)")"
    echo -e "Environment settings: MODULES ["$EGEOFFREY_MODULES"] | GATEWAY ["$EGEOFFREY_GATEWAY_HOSTNAME" "$EGEOFFREY_GATEWAY_PORT" v"$EGEOFFREY_GATEWAY_VERSION"] | HOUSE ["$EGEOFFREY_ID"]"
# welcome message (sdk)
else
    echo -e "SDK v"$(extract version $SDK_MANIFEST |xargs printf '%.1f')"-"$(extract revision $SDK_MANIFEST)" ("$(extract branch $SDK_MANIFEST)")"
fi

# execute eGeoffrey
if [ "$1" = 'egeoffrey' ]; then
    # run user setup script if found
    if [ -f "./docker-init.sh" ]; then 
        echo -e "Running init script..."
        ./docker-init.sh
    fi
    # start eGeoffrey watchdog service
    echo -e "Starting watchdog..."
    if [ $LANGUAGE = "python" ]; then
        exec python -m sdk.python.module.start
    elif [ $LANGUAGE = "python3" ]; then
        exec python3 -m sdk.python3.module.start
    else
        echo "ERROR: unsupported language "$LANGUAGE
        exit
    fi
fi

# execute the provided command
exec "$@"