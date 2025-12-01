#!/bin/bash

source ./watchdog_configure.sh || {
  echo "Failed to source watchdog_configure.sh"
  exit 1
}

docker run --name webbot_container -d \
  -p 5901:5900 -p 6080:6080 \
  --device /dev/bus/usb:/dev/bus/usb \
  --privileged \
  -e VNC_PASSWORD="$VNC_PASSWORD" \
  -e VH_HOST="$VH_HOST" \
  -e VH_PORT="$VH_PORT" \
  -e VH_DEVICE="$VH_DEVICE" \
  webbot



