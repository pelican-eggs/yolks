#!/bin/bash

#
# Copyright (c) 2021 Matthew Penner and contributors
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

# Wait for the container to fully initialize
sleep 1

# Default the TZ environment variable to UTC.
TZ=${TZ:-UTC}
export TZ

# Set environment variable that holds the Internal Docker IP
INTERNAL_IP=$(ip route get 1 | awk '{print $(NF-2);exit}')
export INTERNAL_IP

# Set environment for Steam Proton
if [ -f "/usr/local/bin/proton" ]; then
    if [ ! -z ${SRCDS_APPID} ]; then
	    mkdir -p /home/container/.steam/steam/steamapps/compatdata/${SRCDS_APPID}
        export STEAM_COMPAT_CLIENT_INSTALL_PATH="/home/container/.steam/steam"
        export STEAM_COMPAT_DATA_PATH="/home/container/.steam/steam/steamapps/compatdata/${SRCDS_APPID}"
        # Fix for pipx with protontricks
        export PATH=$PATH:/root/.local/bin
    else
        echo -e "----------------------------------------------------------------------------------"
        echo -e "WARNING!!! Proton needs variable SRCDS_APPID, else it will not work. Please add it"
        echo -e "Server stops now"
        echo -e "----------------------------------------------------------------------------------"
        exit 1
        fi
fi

# Switch to the container's working directory
cd /home/container || exit 1

## Update server via SteamCMD if AUTO_UPDATE is 1 or not set
if [ -z ${AUTO_UPDATE} ] || [ "${AUTO_UPDATE}" == "1" ]; then
    echo -e "Checking for game server updates..."
    # Check for set App ID
    if [ ! -z ${SRCDS_APPID} ]; then
        # Set default credentials if they are missing
        if [ "${STEAM_USER}" == "" ]; then
            echo -e "Steam user is not set. Defaulting to anonymous user."
            STEAM_USER=anonymous
            STEAM_PASS=""
            STEAM_AUTH=""
        fi
        # Run SteamCMD
        ./steamcmd/steamcmd.sh +force_install_dir /home/container +login ${STEAM_USER} ${STEAM_PASS} ${STEAM_AUTH} $( [[ "${WINDOWS_INSTALL}" == "1" ]] && printf %s '+@sSteamCmdForcePlatformType windows' ) +app_update 1007 +app_update ${SRCDS_APPID} $( [[ -z ${SRCDS_BETAID} ]] || printf %s "-beta ${SRCDS_BETAID}" ) $( [[ -z ${SRCDS_BETAPASS} ]] || printf %s "-betapassword ${SRCDS_BETAPASS}" ) $( [[ -z ${HLDS_GAME} ]] || printf %s "+app_set_config 90 mod ${HLDS_GAME}" ) ${INSTALL_FLAGS} $( [[ "${VALIDATE}" == "1" ]] && printf %s 'validate' ) +quit
    else
        echo -e "No App ID set! Skipping check."
    fi
else
    echo -e "Skipping game server update check; Auto Update is set to 0."
fi

# Replace Startup Variables
modifiedStartup=`eval echo $(echo ${STARTUP} | sed -e 's/{{/${/g' -e 's/}}/}/g')`

# Run the Server
echo -e "Starting server..."
echo -e ":/home/container$ ${modifiedStartup}"
${modifiedStartup}
