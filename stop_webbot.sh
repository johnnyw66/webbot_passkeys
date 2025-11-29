#!/bin/bash

CONTAINER_NAME="webbot_container"

if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}\$"; then
    echo "Stopping container $CONTAINER_NAME..."
    docker stop "$CONTAINER_NAME"
    docker rm "$CONTAINER_NAME"
    echo "Container $CONTAINER_NAME stopped and removed."
else
    echo "No container named $CONTAINER_NAME found."
fi


