#!/bin/bash
# Start VirtualHere in background
/usr/local/bin/vhusbd -b -c /root/.vh/config.ini -r /root/.vh/vhusbd.log
# Keep container alive so Docker PID 1 doesn’t exit
tail -f /root/.vh/vhusbd.log

