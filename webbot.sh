#!/bin/bash
hostname=$(hostname)
source /opt/playwright-env/bin/activate
touch /root/.Xauthority
while [[ true ]]; do
 echo "*** WARNING - CHECK YOU HAVE vhclient running if using a remote FIDO device ***"
 python3 webbot.py $@
 sleep 1
done



