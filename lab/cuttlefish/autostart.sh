#!/bin/bash
set -u

# run_services.sh ends in tail -f, so it has to go to the background
/root/run_services.sh &

# wait for the bridge, otherwise crosvm cannot write to the tap device
for i in $(seq 1 30); do
    ip link show cvd-ebr >/dev/null 2>&1 && break
    sleep 1
done

cd /cf

# -report_anonymous_usage_stats=n so it does not ask Y/n without a tty
HOME=/cf ./bin/launch_cvd --daemon -report_anonymous_usage_stats=n

wait
