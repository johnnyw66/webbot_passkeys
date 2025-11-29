docker run --name webbot_container -d \
  -p 5901:5900 -p 6080:6080 \
  --device /dev/bus/usb:/dev/bus/usb \
  --privileged \
  -e VNC_PASSWORD="mypassword" \
  webbot



