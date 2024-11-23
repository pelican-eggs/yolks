#!/bin/bash
cd /home/container

# Make internal Docker IP address available to processes.
INTERNAL_IP=$(ip route get 1 | awk '{print $(NF-2);exit}')
export INTERNAL_IP

# Replace Startup Variables
MODIFIED_STARTUP=$(echo -e ${STARTUP} | sed -e 's/{{/${/g' -e 's/}}/}/g')
echo -e ":/home/container$ ${MODIFIED_STARTUP}"

# Run the Server in background and wait until it's ready
eval ${MODIFIED_STARTUP} &

# Wait for the game server to initialize
while ! ps aux | grep '[S]tardewValleys'; do
    echo "Waiting for StardewValleys to start..."
    sleep 2
done

# Notify Pterodactyl that the server is online
echo "StardewValleys is now online!"
