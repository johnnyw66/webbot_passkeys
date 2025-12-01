#!/bin/bash

mkdir -p "$PWD/vh_data"

docker run -d \
  --name virtualhere_container \
  --privileged \
  --restart unless-stopped \
  -p 7575:7575 \
  --device /dev/bus/usb:/dev/bus/usb \
  -v "$(pwd)/vh_data:/root/.vh" \
  virtualhere-pi5
