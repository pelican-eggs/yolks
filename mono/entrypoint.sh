#!/bin/bash
# Wait for the container to fully initialize
sleep 1

# Default the TZ environment variable to UTC.
TZ=${TZ:-UTC}
export TZ

# Set environment variable that holds the Internal Docker IP
INTERNAL_IP=$(ip route get 1 | awk '{print $(NF-2);exit}')
export INTERNAL_IP

# Switch to the container's working directory
cd /home/container || exit 1

if [ ! -z "${SRCDS_APPID}" ]; then
    ## just in case someone removed the defaults.
    if [ "${STEAM_USER}" == "" ]; then
        echo -e "steam user is not set.\n"
        echo -e "Using anonymous user.\n"
        STEAM_USER=anonymous
        STEAM_PASS=""
        STEAM_AUTH=""
    else
        echo -e "user set to ${STEAM_USER}"
    fi

    ## if auto_update is not set or to 1 update
    if [ -z ${AUTO_UPDATE} ] || [ "${AUTO_UPDATE}" == "1" ]; then 
        # Update Source Server
        if [ ! -z ${SRCDS_APPID} ]; then
            ./steamcmd/steamcmd.sh +force_install_dir /home/container +login ${STEAM_USER} ${STEAM_PASS} ${STEAM_AUTH} $( [[ "${WINDOWS_INSTALL}" == "1" ]] && printf %s '+@sSteamCmdForcePlatformType windows' ) +app_update 1007 +app_update ${SRCDS_APPID} $( [[ -z ${SRCDS_BETAID} ]] || printf %s "-beta ${SRCDS_BETAID}" ) $( [[ -z ${SRCDS_BETAPASS} ]] || printf %s "-betapassword ${SRCDS_BETAPASS}" ) $( [[ -z ${HLDS_GAME} ]] || printf %s "+app_set_config 90 mod ${HLDS_GAME}" ) $( [[ -z ${VALIDATE} ]] || printf %s "validate" ) +quit
        else
            echo -e "No appid set. Starting Server"
        fi

    else
        echo -e "Not updating game server as auto update was set to 0. Starting Server"
    fi
fi


# Replace Startup Variables
MODIFIED_STARTUP=$(echo ${STARTUP} | sed -e 's/{{/${/g' -e 's/}}/}/g')
echo -e ":/home/container$ ${MODIFIED_STARTUP}"

# Run the Server
eval ${MODIFIED_STARTUP}
