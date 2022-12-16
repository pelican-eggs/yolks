#!/bin/bash
cd /home/container

# Set environment variable that holds the Internal Docker IP
INTERNAL_IP=$(ip route get 1 | awk '{print $(NF-2);exit}')
export INTERNAL_IP

# Replace Startup Variables
MODIFIED_STARTUP=$(echo -e $(echo -e ${STARTUP} | sed -e 's/{{/${/g' -e 's/}}/}/g'))
echo -e ":/home/container$ ${MODIFIED_STARTUP}"

# start mongo
mongod --fork --dbpath /home/container/mongodb/ --port 27017 --logpath /home/container/mongod.log && until nc -z -v -w5 127.0.0.1 27017; do echo 'Waiting for mongodb connection...'; sleep 5; done

# Run the Server
eval ${MODIFIED_STARTUP}

# stop mongo
mongo --eval \"db.getSiblingDB('admin').shutdownServer()\"
