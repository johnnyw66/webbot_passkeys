#!/bin/bash
CLEAN=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --clean)
            CLEAN=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

if $CLEAN; then
    echo "Running clean step..."
    rm -rf /tmp/playwright-profile
fi

hostname=$(hostname)

if [[ -f "/opt/playwright-env/bin/activate" ]]; then
    echo "Source Python Env"
    source /opt/playwright-env/bin/activate
fi

touch /root/.Xauthority
while [[ true ]]; do
 echo "*** WARNING - CHECK YOU HAVE vhclient running if using a remote FIDO device ***"
 python3 webbot.py $@
 sleep 1
done



