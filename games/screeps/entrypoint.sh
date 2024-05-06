#!/bin/bash

cd /home/container

. $NVM_DIR/nvm.sh

echo screeps version: && npm ls screeps

export MODIFIED_STARTUP=`eval echo $(echo ${STARTUP} | sed -e 's/{{/${/g' -e 's/}}/}/g')`
echo ":/home/container$ ${MODIFIED_STARTUP}"

if [ -e .screeps_initialized ]
then
    npm update screeps
    ${MODIFIED_STARTUP}
else
    npm install screeps
    npx screeps init <<< "$STEAM_API_KEY"
    touch .screeps_initialized
    ${MODIFIED_STARTUP}
fi
