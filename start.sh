#!/bin/bash

# start off vhclient

if [ -n "$VH_HOST" ] && [ -n "$VH_PORT" ] && [ -n "$VH_DEVICE" ] && [ -x "/usr/local/bin/vhclient" ] ; then
    echo "Starting VirtualHere client in background..."
    vhclient &

    # Give it a few seconds to initialize
    sleep 4
    echo "Adding remote hub and claiming device..."
    vhclient -t "MANUAL HUB ADD,${VH_HOST}:${VH_PORT}"
    sleep 4
    vhclient -t "USE,${VH_DEVICE}"
else
    echo "VH_HOST, VH_PORT, or VH_DEVICE not set. Skipping VirtualHere client setup."
fi

# Activate virtual environment
source /opt/playwright-env/bin/activate

# Run Python script in background, log output
if [ -f /app/startup.py ]; then
    python -u /app/startup.py > /app/startup.log 2>&1 &
fi

# Start the GUI / VNC / Chromium stack
exec "$@"

