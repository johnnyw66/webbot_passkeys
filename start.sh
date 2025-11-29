#!/bin/bash
# Activate virtual environment
source /opt/playwright-env/bin/activate

# Run Python script in background, log output
if [ -f /app/hello.py ]; then
    python -u /app/hello.py > /app/hello.log 2>&1 &
fi

# Start the GUI / VNC / Chromium stack
exec "$@"

