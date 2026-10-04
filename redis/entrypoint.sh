#!/bin/bash
cd /home/container

INTERNAL_IP=$(ip route get 1 | awk '{print $(NF-2);exit}')
export INTERNAL_IP

MODIFIED_STARTUP=$(echo -e ${STARTUP} | sed -e 's/{{/${/g' -e 's/}}/}/g')
echo ":/home/container$ ${MODIFIED_STARTUP}"

eval ${MODIFIED_STARTUP} &
REDIS_PID=$!

for i in $(seq 1 60); do
    if /usr/local/bin/redis-cli -p "${SERVER_PORT}" -a "${SERVER_PASSWORD}" --no-auth-warning PING 2>/dev/null | grep -q PONG; then
        break
    fi
    sleep 0.5
done

(
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        printf '%s\n' "$line" | /usr/local/bin/redis-cli -p "${SERVER_PORT}" -a "${SERVER_PASSWORD}" --no-auth-warning
    done
) < /dev/stdin &
READER_PID=$!

wait $REDIS_PID
kill $READER_PID 2>/dev/null