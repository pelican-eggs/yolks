#!/bin/bash

## File: Pterodactyl Arma 3 Image - entrypoint.sh
## Author: David Wolfe (Red-Thirten)
## Contributors: Aussie Server Hosts (https://aussieserverhosts.com/)
## Date: 2021/07/13
## License: MIT License

## === CONSTANTS ===
STEAMCMD_DIR="./steamcmd"                       # SteamCMD's directory containing steamcmd.sh
STEAMCMD_LOG="${STEAMCMD_DIR}/steamcmd.log"     # Log file for SteamCMD
GAME_ID=107410                                  # SteamCMD ID for the Arma 3 GAME (not server). Only used for Workshop mod downloads.
EGG_URL='https://github.com/parkervcp/eggs/tree/master/game_eggs/steamcmd_servers/arma/arma3'   # URL for Pterodactyl Egg & Info (only used as info to legacy users)

# Color Codes
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

## === ENVIRONMENT VARS ===
# STARTUP, STARTUP_PARAMS, STEAM_USER, STEAM_PASS, SERVER_BINARY, MOD_FILE, MODIFICATIONS, SERVERMODS, UPDATE_SERVER, CLEAR_CACHE, VALIDATE_SERVER, MODS_LOWERCASE, STEAMCMD_EXTRA_FLAGS, CDLC, STEAMCMD_APPID, HC_NUM, SERVER_PASSWORD, HC_HIDE, STEAMCMD_ATTEMPTS, BASIC_URL, DISABLE_MOD_UPDATES

## === GLOBAL VARS ===
# validateServer, extraFlags, updateAttempt, modifiedStartup, allMods, CLIENT_MODS

## === DEFINE FUNCTIONS ===
#
# Runs SteamCMD with specified variables and performs error handling.
function RunSteamCMD { #[Input: int server=0 mod=1; int id]
    # Clear previous SteamCMD log
    if [[ -f "${STEAMCMD_LOG}" ]]; then
        rm -f "${STEAMCMD_LOG:?}"
    fi
    
    updateAttempt=0
    while (( $updateAttempt < $STEAMCMD_ATTEMPTS )); do # Loop for specified number of attempts
        # Increment attempt counter
        updateAttempt=$((updateAttempt+1))
        
        if (( $updateAttempt > 1 )); then # Notify if not first attempt
            echo -e "\t${YELLOW}Re-Attempting download/update in 3 seconds...${NC} (Attempt ${CYAN}${updateAttempt}${NC} of ${CYAN}${STEAMCMD_ATTEMPTS}${NC})\n"
            sleep 3
        fi
        
        # Check if updating server or mod
        if [[ $1 == 0 ]]; then # Server
            ${STEAMCMD_DIR}/steamcmd.sh +force_install_dir /home/container "+login \"${STEAM_USER}\" \"${STEAM_PASS}\"" +app_update $2 $extraFlags $validateServer +quit | tee -a "${STEAMCMD_LOG}"
        else # Mod
            ${STEAMCMD_DIR}/steamcmd.sh "+login \"${STEAM_USER}\" \"${STEAM_PASS}\"" +workshop_download_item $GAME_ID $2 +quit | tee -a "${STEAMCMD_LOG}"
        fi
        
        # Error checking for SteamCMD
        steamcmdExitCode=${PIPESTATUS[0]}
        if [[ -n $(grep -i "error\|failed" "${STEAMCMD_LOG}" | grep -iv "setlocal\|SDL") ]]; then # Catch errors (ignore setlocale and SDL warnings)
            # Soft errors
            if [[ -n $(grep -i "Timeout downloading item" "${STEAMCMD_LOG}") ]]; then # Mod download timeout
                echo -e "\n${YELLOW}[UPDATE]: ${NC}Timeout downloading Steam Workshop mod: \"${CYAN}${modName}${NC}\" (${CYAN}${2}${NC})"
                echo -e "\t(This is expected for particularly large mods)"
            elif [[ -n $(grep -i "0x402\|0x6\|0x602" "${STEAMCMD_LOG}") ]]; then # Connection issue with Steam
                echo -e "\n${YELLOW}[UPDATE]: ${NC}Connection issue with Steam servers."
                echo -e "\t(Steam servers may currently be down, or a connection cannot be made reliably)"
            # Hard errors
            elif [[ -n $(grep -i "Password check for AppId" "${STEAMCMD_LOG}") ]]; then # Incorrect beta branch password
                echo -e "\n${RED}[UPDATE]: ${YELLOW}Incorrect password given for beta branch. ${CYAN}Skipping download...${NC}"
                echo -e "\t(Check your \"[ADVANCED] EXTRA FLAGS FOR STEAMCMD\" startup parameter)"
                break
            # Fatal errors
            elif [[ -n $(grep -i "Invalid Password\|two-factor\|No subscription" "${STEAMCMD_LOG}") ]]; then # Wrong username/password, Steam Guard is turned on, or host is using anonymous account
                echo -e "\n${RED}[UPDATE]: Cannot login to Steam - Improperly configured account and/or credentials"
                echo -e "\t${YELLOW}Please contact your administrator/host and give them the following message:${NC}"
                echo -e "\t${CYAN}Your Egg, or your client's server, is not configured with valid Steam credentials.${NC}"
                echo -e "\t${CYAN}Either the username/password is wrong, or Steam Guard is not properly configured\n\taccording to this egg's documentation/README.${NC}\n"
                exit 1
            elif [[ -n $(grep -i "Download item" "${STEAMCMD_LOG}") ]]; then # Steam account does not own base game for mod downloads, or unknown
                echo -e "\n${RED}[UPDATE]: Cannot download mod - Download failed"
                echo -e "\t${YELLOW}While unknown, this error is likely due to your host's Steam account not owning the base game.${NC}"
                echo -e "\t${YELLOW}(Please contact your administrator/host if this issue persists)${NC}\n"
                exit 1
            elif [[ -n $(grep -i "0x202\|0x212" "${STEAMCMD_LOG}") ]]; then # Not enough disk space
                echo -e "\n${RED}[UPDATE]: Unable to complete download - Not enough storage"
                echo -e "\t${YELLOW}You have run out of your allotted disk space.${NC}"
                echo -e "\t${YELLOW}Please contact your administrator/host for potential storage upgrades.${NC}\n"
                exit 1
            elif [[ -n $(grep -i "0x606" "${STEAMCMD_LOG}") ]]; then # Disk write failure
                echo -e "\n${RED}[UPDATE]: Unable to complete download - Disk write failure"
                echo -e "\t${YELLOW}This is normally caused by directory permissions issues,\n\tbut could be a more serious hardware issue.${NC}"
                echo -e "\t${YELLOW}(Please contact your administrator/host if this issue persists)${NC}\n"
                exit 1
            else # Unknown caught error
                echo -e "\n${RED}[UPDATE]: ${YELLOW}An unknown error has occurred with SteamCMD. ${CYAN}Skipping download...${NC}"
                echo -e "\t(Please contact your administrator/host if this issue persists)"
                break
            fi
        elif [[ $steamcmdExitCode != 0 ]]; then # Unknown fatal error
            echo -e "\n${RED}[UPDATE]: SteamCMD has crashed for an unknown reason!${NC} (Exit code: ${CYAN}${steamcmdExitCode}${NC})"
            echo -e "\t${YELLOW}(Please contact your administrator/host for support)${NC}\n"
            exit $steamcmdExitCode
        else # Success!
            if [[ $1 == 0 ]]; then # Server
                echo -e "\n${GREEN}[UPDATE]: Game server is up to date!${NC}"
            else # Mod
                # Move the downloaded mod to the root directory, and replace existing mod if needed
                mkdir -p ./@$2
                rm -rf ./@$2/*
                mv -f ./Steam/steamapps/workshop/content/$GAME_ID/$2/* ./@$2
                rm -d ./Steam/steamapps/workshop/content/$GAME_ID/$2
                # Make the mods contents all lowercase
                ModsLowercase @$2
                # Move any .bikey's to the keys directory
                echo -e "\tMoving any mod ${CYAN}.bikey${NC} files to the ${CYAN}~/keys/${NC} folder..."
                find ./@$2 -name "*.bikey" -type f -exec cp {} ./keys \;
                echo -e "${GREEN}[UPDATE]: Mod download/update successful!${NC}"
            fi
            break
        fi
        if (( $updateAttempt == $STEAMCMD_ATTEMPTS )); then # Notify if failed last attempt
            if [[ $1 == 0 ]]; then # Server
                echo -e "\t${RED}Final attempt made! ${YELLOW}Unable to complete game server update. ${CYAN}Skipping...${NC}"
                echo -e "\t(Please try again at a later time)"
                sleep 3
            else # Mod
                echo -e "\t${RED}Final attempt made! ${YELLOW}Unable to complete mod download/update. ${CYAN}Skipping...${NC}"
                echo -e "\t(You may try again later, or manually upload this mod to your server via SFTP)"
                sleep 3
            fi
        fi
    done
}

# Takes a directory (string) as input, and recursively makes all files & folders lowercase.
function ModsLowercase {
    echo -e "\n\tMaking mod ${CYAN}$1${NC} files/folders lowercase..."
    for SRC in `find ./$1 -depth`
    do
        DST=`dirname "${SRC}"`/`basename "${SRC}" | tr '[A-Z]' '[a-z]'`
        if [ "${SRC}" != "${DST}" ]
        then
            [ ! -e "${DST}" ] && mv -T "${SRC}" "${DST}"
        fi
    done
}

# Removes duplicate items from a semicolon delimited string
function RemoveDuplicates { #[Input: str - Output: printf of new str]
    if [[ -n $1 ]]; then # If nothing to compare, skip to prevent extra semicolon being returned
        echo $1 | sed -e 's/;/\n/g' | sort -u | xargs printf '%s;'
    fi
}

# === ENTRYPOINT START ===
cd /home/container
sleep 1

# Check for old eggs
if [[ -z ${VALIDATE_SERVER} ]]; then # VALIDATE_SERVER was not in the previous version
    echo -e "\n${RED}[STARTUP_ERR]: Please contact your administrator/host for support, and give them the following message:${NC}\n"
    echo -e "\t${CYAN}Your Arma 3 Egg is outdated and no longer supported.${NC}"
    echo -e "\t${CYAN}Please download the latest version at the following link, and install it in your panel:${NC}"
    echo -e "\t${CYAN}${EGG_URL}${NC}\n"
    exit 1
fi

# Collect and parse all specified mods
if [[ -n ${MODIFICATIONS} ]] && [[ ${MODIFICATIONS} != *\; ]]; then # Add manually specified mods to the client-side mods list, while checking for trailing semicolon
    CLIENT_MODS="${MODIFICATIONS};"
else
    CLIENT_MODS=${MODIFICATIONS}
fi
if [[ -f ${MOD_FILE} ]] && [[ -n "$(cat ${MOD_FILE} | grep 'Created by Arma 3 Launcher')" ]]; then # If the mod list file exists and is valid, parse and add mods to the client-side mods list
    CLIENT_MODS+=$(cat ${MOD_FILE} | grep 'id=' | cut -d'=' -f3 | cut -d'"' -f1 | xargs printf '@%s;')
elif [[ -n "${MOD_FILE}" ]]; then # If MOD_FILE is not null, warn user file is missing or invalid
    echo -e "\n${YELLOW}[STARTUP_WARN]: Arma 3 Modlist file \"${CYAN}${MOD_FILE}${YELLOW}\" could not be found, or is invalid!${NC}"
    echo -e "\tEnsure your uploaded modlist's file name matches your Startup Parameter."
    echo -e "\tOnly files exported from an Arma 3 Launcher are permitted."
    if [[ -n "${CLIENT_MODS}" ]]; then
        echo -e "\t${CYAN}Reverting to the manual mod list...${NC}"
    fi
fi
if [[ -n ${SERVERMODS} ]] && [[ ${SERVERMODS} != *\; ]]; then # Add server mods to the master mods list, while checking for trailing semicolon
    allMods="${SERVERMODS};"
else
    allMods=${SERVERMODS}
fi
allMods+=$CLIENT_MODS # Add all client-side mods to the master mod list
CLIENT_MODS=$(RemoveDuplicates ${CLIENT_MODS}) # Remove duplicate mods from CLIENT_MODS, if present
allMods=$(RemoveDuplicates ${allMods}) # Remove duplicate mods from allMods, if present
allMods=$(echo $allMods | sed -e 's/;/ /g') # Convert from string to array

# Update everything (server and mods), if specified
if [[ ${UPDATE_SERVER} == 1 ]]; then
    echo -e "\n${GREEN}[STARTUP]: ${CYAN}Starting checks for all updates...${NC}"
    echo -e "(It is okay to ignore any \"SDL\" errors during this process)\n"
    
    ## Update game server
    echo -e "${GREEN}[UPDATE]:${NC} Checking for game server updates with App ID: ${CYAN}${STEAMCMD_APPID}${NC}..."
    
    if [[ ${VALIDATE_SERVER} == 1 ]]; then # Validate will be added as a parameter if specified
        echo -e "\t${CYAN}File validation enabled.${NC} (This may take extra time to complete)"
        validateServer="validate"
    else
        validateServer=""
    fi
    
    # Determine what extra flags should be set
    if [[ -n ${STEAMCMD_EXTRA_FLAGS} ]]; then
        echo -e "\t(${YELLOW}Advanced${NC}) Extra SteamCMD flags specified: ${CYAN}${STEAMCMD_EXTRA_FLAGS}${NC}\n"
        extraFlags=${STEAMCMD_EXTRA_FLAGS}
    elif [[ ${CDLC} == 1 ]]; then
        echo -e "\t${CYAN}Download/Update Creator DLC server files enabled.${NC}\n"
        extraFlags="-beta creatordlc"
    else
        echo -e ""
        extraFlags=""
    fi
    
    RunSteamCMD 0 ${STEAMCMD_APPID}
    
    ## Update mods
    if [[ -n $allMods ]] && [[ ${DISABLE_MOD_UPDATES} != 1 ]]; then
        echo -e "\n${GREEN}[UPDATE]:${NC} Checking all ${CYAN}Steam Workshop mods${NC} for updates..."
        for modID in $(echo $allMods | sed -e 's/@//g')
        do
            if [[ $modID =~ ^[0-9]+$ ]]; then # Only check mods that are in ID-form
                # Get mod's latest update in epoch time from its Steam Workshop changelog page
                latestUpdate=$(curl -sL https://steamcommunity.com/sharedfiles/filedetails/changelog/$modID | grep '<p id=' | head -1 | cut -d'"' -f2)
                # If the update time is valid and newer than the local directory's creation date, or the mod hasn't been downloaded yet, download the mod
                if [[ ! -d @$modID ]] || [[ ( -n $latestUpdate ) && ( $latestUpdate =~ ^[0-9]+$ ) && ( $latestUpdate > $(find @$modID | head -1 | xargs stat -c%Y) ) ]]; then
                    # Get the mod's name from the Workshop page as well
                    modName=$(curl -sL https://steamcommunity.com/sharedfiles/filedetails/changelog/$modID | grep 'workshopItemTitle' | cut -d'>' -f2 | cut -d'<' -f1)
                    if [[ -z $modName ]]; then # Set default name if unavailable
                        modName="[NAME UNAVAILABLE]"
                    fi
                    if [[ ! -d @$modID ]]; then
                        echo -e "\n${GREEN}[UPDATE]:${NC} Downloading new Mod: \"${CYAN}${modName}${NC}\" (${CYAN}${modID}${NC})"
                    else
                        echo -e "\n${GREEN}[UPDATE]:${NC} Mod update found for: \"${CYAN}${modName}${NC}\" (${CYAN}${modID}${NC})"
                    fi
                    if [[ -n $latestUpdate ]] && [[ $latestUpdate =~ ^[0-9]+$ ]]; then # Notify last update date, if valid
                        echo -e "\tMod was last updated: ${CYAN}$(date -d @${latestUpdate})${NC}"
                    fi
                    echo -e "\tAttempting mod update/download via SteamCMD...\n"
                    RunSteamCMD 1 $modID
                fi
            fi
        done
        echo -e "${GREEN}[UPDATE]:${NC} Steam Workshop mod update check ${GREEN}complete${NC}!"
    fi
fi

# Check if specified server binary exists.
if [[ ! -f ./${SERVER_BINARY} ]]; then
    echo -e "\n${RED}[STARTUP_ERR]: Specified Arma 3 server binary could not be found in the root directory!${NC}"
    echo -e "${YELLOW}Please do the following to resolve this issue:${NC}"
    echo -e "\t${CYAN}- Double check your \"Server Binary\" Startup Variable is correct.${NC}"
    echo -e "\t${CYAN}- Ensure your server has properly installed/updated without errors (reinstalling/updating again may help).${NC}"
    echo -e "\t${CYAN}- Use the File Manager to check that your specified server binary file is not missing from the root directory.${NC}\n"
    exit 1
fi

# Make mods lowercase, if specified
if [[ ${MODS_LOWERCASE} == "1" ]]; then
    for modDir in $allMods
    do
        ModsLowercase $modDir
    done
fi

# Clear HC cache, if specified
if [[ ${CLEAR_CACHE} == "1" ]]; then
    echo -e "\n${GREEN}[STARTUP]: ${CYAN}Clearing Headless Client profiles cache...${NC}"
    for profileDir in ./serverprofile/home/*
    do
        [ "$profileDir" = "./serverprofile/home/Player" ] && continue
        rm -rf $profileDir
    done
fi

# Check if basic.cfg exists, and download if not (Arma really doesn't like it missing for some reason)
if [[ ! -f ./basic.cfg ]]; then
    echo -e "\n${YELLOW}[STARTUP_WARN]: Basic Network Configuration file \"${CYAN}basic.cfg${YELLOW}\" is missing!${NC}"
    echo -e "\t${YELLOW}Downloading default file for use instead...${NC}"
    curl -sSL ${BASIC_URL} -o ./basic.cfg
fi

# $NSS_WRAPPER_PASSWD and $NSS_WRAPPER_GROUP have been set by the Dockerfile
export USER_ID=$(id -u)
export GROUP_ID=$(id -g)
envsubst < /passwd.template > ${NSS_WRAPPER_PASSWD}

if [[ ${SERVER_BINARY} == *"x64"* ]]; then # Check which libnss_wrapper architecture to run, based off the server binary name
    export LD_PRELOAD=/libnss_wrapper_x64.so
else
    export LD_PRELOAD=/libnss_wrapper.so
fi

# Replace Startup Variables
modifiedStartup=`eval echo $(echo ${STARTUP} | sed -e 's/{{/${/g' -e 's/}}/}/g')`

# Start Headless Clients if applicable
if [[ ${HC_NUM} > 0 ]]; then
    echo -e "\n${GREEN}[STARTUP]:${NC} Starting ${CYAN}${HC_NUM}${NC} Headless Client(s)."
    for i in $(seq ${HC_NUM})
    do
        if [[ ${HC_HIDE} == "1" ]];
        then
            ./${SERVER_BINARY} -client -connect=127.0.0.1 -port=${SERVER_PORT} -password="${SERVER_PASSWORD}" -profiles=./serverprofile -bepath=./battleye -mod="${CLIENT_MODS}" ${STARTUP_PARAMS} > /dev/null 2>&1 &
        else
            ./${SERVER_BINARY} -client -connect=127.0.0.1 -port=${SERVER_PORT} -password="${SERVER_PASSWORD}" -profiles=./serverprofile -bepath=./battleye -mod="${CLIENT_MODS}" ${STARTUP_PARAMS} &
        fi
        echo -e "${GREEN}[STARTUP]:${CYAN} Headless Client $i${NC} launched."
    done
fi

# Start the Server
echo -e "\n${GREEN}[STARTUP]:${NC} Starting server with the following startup command:"
echo -e "${CYAN}${modifiedStartup}${NC}\n"
${modifiedStartup}

if [ $? -ne 0 ]; then
    echo -e "\n${RED}PTDL_CONTAINER_ERR: There was an error while attempting to run the start command.${NC}\n"
    exit 1
fi
