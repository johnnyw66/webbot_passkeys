#!/bin/bash
hostname=$(hostname)
source /opt/playwright-env/bin/activate
touch /root/.Xauthority
while [[ true ]]; do
 python3 webbot.py $@
 #python3 message.py "From host `hostname`. Webbot terminated ...`date`"
 #./announce.sh "We have logged out of $hostname"
 python3 pause.py
done



