#!/bin/bash
cd /home/container

# Set environment variable that holds the Internal Docker IP
INTERNAL_IP=$(ip route get 1 | awk '{print $(NF-2);exit}')
export INTERNAL_IP

# set this variable, dotnet needs it even without it it reports to `dotnet --info` it can not start any aplication without this
export DOTNET_ROOT=/usr/share/

# print the dotnet version on startup
printf "\033[1m\033[33mcontainer~ \033[0mdotnet --version\n"
dotnet --version

# Replace Startup Variables
MODIFIED_STARTUP=$(echo -e ${STARTUP} | sed -e 's/{{/${/g' -e 's/}}/}/g')
echo -e ":/home/container$ ${MODIFIED_STARTUP}"

# Run the Server
eval ${MODIFIED_STARTUP}
