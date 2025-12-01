#!/bin/bash
chmod +x *.sh

# Collect only arguments starting with --
DOCKER_ARGS=()
for arg in "$@"; do
    if [[ "$arg" == --* ]]; then
        DOCKER_ARGS+=("$arg")
    fi
done

# Run docker build with the filtered arguments and default context
docker build "${DOCKER_ARGS[@]}" -f Dockerfile.freeze -t webbot .

