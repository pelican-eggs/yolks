#!/bin/bash

# Default the TZ environment variable to UTC.
TZ=${TZ:-UTC}
export TZ

# Simple colors via tput (fallback to no color if unavailable)
RED=$(tput setaf 1 2>/dev/null || echo '')
GREEN=$(tput setaf 2 2>/dev/null || echo '')
YELLOW=$(tput setaf 3 2>/dev/null || echo '')
BLUE=$(tput setaf 4 2>/dev/null || echo '')
CYAN=$(tput setaf 6 2>/dev/null || echo '')
NC=$(tput sgr0 2>/dev/null || echo '')

ERROR_LOG="/home/container/install_error.log"

# Message helpers
msg() {
    local color="$1"
    shift
    # If RED, also write the message to install_error.log
    if [ "$color" = "RED" ]; then
        printf "%b\n" "${RED}$*${NC}" | tee -a "$ERROR_LOG" >&2
    else
        printf "%b\n" "${!color}$*${NC}"
    fi
}

line() {
    local color="${1:-BLUE}"
    local term_width
    term_width=$(tput cols 2>/dev/null || echo 70)
    local sep
    sep=$(printf '%*s' "$term_width" '' | tr ' ' '-')
    msg "$color" "$sep"
}

# Set environment variable that holds the Internal Docker IP
INTERNAL_IP=$(ip route get 1 | awk '{print $(NF-2);exit}')
export INTERNAL_IP

# Switch to the container's working directory
cd /home/container || exit 1

# Refresh temporary directory to avoid stale downloads between restarts
rm -rf /home/container/.tmp
mkdir -p /home/container/.tmp

# Print Java version
echo "java -version"
java -version

# Cleanup invalid version file (e.g., if it contains auth prompts)
if [ -f "/home/container/.version" ]; then
    if ! grep -qE '^[0-9]{4}\.[0-9]{2}\.[0-9]{2}-[a-f0-9]+' "/home/container/.version"; then
        msg YELLOW "Warning: Invalid .version content detected; removing file"
        rm -f "/home/container/.version"
    fi
fi

# Hytale Downloader Configuration
DOWNLOADER_URL="https://downloader.hytale.com/hytale-downloader.zip"
DOWNLOADER_BIN="${DOWNLOADER_BIN:-/home/container/hytale-downloader}"
AUTO_UPDATE=${AUTO_UPDATE:-0}
PATCHLINE=${PATCHLINE:-release}
CREDENTIALS_PATH="${CREDENTIALS_PATH:-/home/container/.hytale-downloader-credentials.json}"
DOWNLOADER_ARGS=()

# Plugin Configuration
PSAVER=${PSAVER:-0}
PSAVER_RELEASES_URL="https://api.github.com/repos/nitrado/hytale-plugin-performance-saver/releases/latest"
PSAVER_PLUGINS_DIR="/home/container/mods"
PSAVER_JAR_PATTERN="Nitrado_PerformanceSaver*.jar"

# Auth is handled manually via URL; credentials file is optional but used when present
if [ -n "$CREDENTIALS_PATH" ] && [ -f "$CREDENTIALS_PATH" ]; then
    DOWNLOADER_ARGS+=("-credentials-path" "$CREDENTIALS_PATH")
fi

# Check for downloader updates first thing
if [ -f "$DOWNLOADER_BIN" ]; then
    msg BLUE "[startup] Checking for downloader updates..."
    if "$DOWNLOADER_BIN" "${DOWNLOADER_ARGS[@]}" -check-update 2>&1 | sed "s/.*/  ${CYAN}&${NC}/"; then
        msg GREEN "  ✓ Downloader is up to date"
        if [ -f "$CREDENTIALS_PATH" ]; then
            msg GREEN "  ✓ Valid downloader auth file found"
        fi
    else
        msg YELLOW "  Note: Downloader update check completed"
    fi
fi

# Function to install Hytale Downloader
install_downloader() {
    msg BLUE "[installer] Downloader not found, installing..."

    local TEMP_DIR="/home/container/.tmp/hytale-downloader-install"
    rm -rf "$TEMP_DIR"
    mkdir -p "$TEMP_DIR"

    # Download downloader
    msg BLUE "[installer] Downloading downloader package..."
    if ! wget -O "$TEMP_DIR/downloader.zip" "$DOWNLOADER_URL"; then
        msg RED "Error: Failed to download Hytale Downloader"
        rm -rf "$TEMP_DIR"
        return 1
    fi

    # Extract downloader
    msg BLUE "[installer] Extracting downloader..."
    if ! unzip -o "$TEMP_DIR/downloader.zip" -d "$TEMP_DIR"; then
        msg RED "Error: Failed to extract Hytale Downloader"
        rm -rf "$TEMP_DIR"
        return 1
    fi

    # Copy to target location
    if [ -f "$TEMP_DIR/hytale-downloader" ]; then
        cp "$TEMP_DIR/hytale-downloader" "$DOWNLOADER_BIN"
        chmod +x "$DOWNLOADER_BIN"
        msg GREEN "✓ Hytale Downloader installed successfully"
    else
        msg RED "Error: Downloader binary not found in archive"
        rm -rf "$TEMP_DIR"
        return 1
    fi

    # Cleanup
    rm -rf "$TEMP_DIR"
    return 0
}

# Check for updates
check_for_updates() {
    msg BLUE "[update] Checking for Hytale server updates..."

    if [ ! -f "$DOWNLOADER_BIN" ]; then
        if ! install_downloader; then
            msg RED "Error: Failed to install Hytale Downloader"
            return 1
        fi
    fi

    # If credentials file does not exist yet, trigger an initial run without args
    # so the downloader can guide through device auth and create the file.
    if [ ! -f "$CREDENTIALS_PATH" ]; then
        msg BLUE "[auth] Initializing downloader to create credentials (one-time)..."
        "$DOWNLOADER_BIN" -print-version -skip-update-check 2>&1 | sed "s/.*/  ${CYAN}&${NC}/"
        if [ -f "$CREDENTIALS_PATH" ]; then
            msg GREEN "  ✓ Credentials file created"
            # Rebuild downloader args now that the file exists
            DOWNLOADER_ARGS=("-credentials-path" "$CREDENTIALS_PATH")
        else
            msg YELLOW "  Note: Credentials file not created yet; continuing without it"
        fi
    fi

    # Get current game version
    CURRENT_VERSION=$(timeout 10 "$DOWNLOADER_BIN" "${DOWNLOADER_ARGS[@]}" -print-version -skip-update-check 2>/dev/null \
        | grep -v -E "Please visit|Path to credentials file|Authorization code:" \
        | head -1)

    if [ -z "$CURRENT_VERSION" ]; then
        msg YELLOW "Warning: Could not determine game version"
        return 1
    fi

    msg GREEN "Current game version: $CURRENT_VERSION"
    return 0
}

# Function to download and update Hytale
download_hytale() {
    msg BLUE "[update] Checking for Hytale updates..."

    if [ ! -f "$DOWNLOADER_BIN" ]; then
        if ! install_downloader; then
            msg RED "Error: Failed to install Hytale Downloader"
            return 1
        fi
    fi

    # If credentials file does not exist yet, trigger an initial run without args
    # so the downloader can guide through device auth and create the file.
    if [ ! -f "$CREDENTIALS_PATH" ]; then
        msg BLUE "[auth] Initializing downloader to create credentials (one-time)..."
        "$DOWNLOADER_BIN" -print-version -skip-update-check 2>&1 | sed "s/.*/  ${CYAN}&${NC}/"
        if [ -f "$CREDENTIALS_PATH" ]; then
            msg GREEN "  ✓ Credentials file created"
            # Rebuild downloader args now that the file exists
            DOWNLOADER_ARGS=("-credentials-path" "$CREDENTIALS_PATH")
        else
            msg YELLOW "  Note: Credentials file not created yet; continuing without it"
        fi
    fi

    # Check local version
    LOCAL_VERSION=""
    if [ -f "/home/container/.version" ]; then
        # Read only a valid version line, ignore any accidental prompt leftovers
        LOCAL_VERSION=$(grep -E '^[0-9]{4}\.[0-9]{2}\.[0-9]{2}-[a-f0-9]+' -m1 \
            "/home/container/.version" 2>/dev/null)
    fi

    msg CYAN "  Local version: ${LOCAL_VERSION:-none installed}"

    # Get remote version without downloading
    msg BLUE "[update 1/3] Fetching remote version..."
    REMOTE_VERSION=$(timeout 10 "$DOWNLOADER_BIN" "${DOWNLOADER_ARGS[@]}" -patchline "$PATCHLINE" -print-version -skip-update-check 2>/dev/null \
        | grep -v -E "Please visit|Path to credentials file|Authorization code:" \
        | head -1)

    if [ -z "$REMOTE_VERSION" ]; then
        msg RED "Error: Could not determine remote version"
        return 1
    fi

    msg CYAN "  Remote version: $REMOTE_VERSION"

    # Compare versions - if same, skip everything
    if [ "$LOCAL_VERSION" = "$REMOTE_VERSION" ] && [ -f "/home/container/HytaleServer.jar" ]; then
        msg GREEN "✓ Already running version $REMOTE_VERSION - no update needed"
        return 0
    fi

    # Version is different, download and install
    msg BLUE "[update 2/3] Downloading Hytale build..."

    # Create temporary directory for download
    DOWNLOAD_DIR="/home/container/.tmp/hytale-download"
    rm -rf "$DOWNLOAD_DIR"
    mkdir -p "$DOWNLOAD_DIR"

    # Run downloader inside download dir so it names the zip itself
    if ! (cd "$DOWNLOAD_DIR" && "$DOWNLOADER_BIN" "${DOWNLOADER_ARGS[@]}" -patchline "$PATCHLINE" -skip-update-check 2>&1 | sed "s/.*/  ${CYAN}&${NC}/"); then
        msg RED "Error: Hytale Downloader failed"
        rm -rf "$DOWNLOAD_DIR"
        return 1
    fi

    # Locate downloaded zip (dynamic name by date/branch)
    GAME_ZIP=$(find "$DOWNLOAD_DIR" -maxdepth 3 -name "*.zip" -type f | head -n 1)

    if [ -z "$GAME_ZIP" ] || [ ! -f "$GAME_ZIP" ]; then
        msg RED "Error: No zip file found in download directory"
        rm -rf "$DOWNLOAD_DIR"
        return 1
    fi

    # Extract downloaded files
    msg BLUE "[update 3/3] Extracting and installing..."
    if ! unzip -o "$GAME_ZIP" -d "$DOWNLOAD_DIR"; then
        msg RED "Error: Failed to extract Hytale server files"
        rm -rf "$DOWNLOAD_DIR"
        return 1
    fi

    # Copy Server folder contents and Assets.zip to container root
    if [ -d "$DOWNLOAD_DIR/Server" ]; then
        # Move all files from Server folder to /home/container
        cp -r "$DOWNLOAD_DIR/Server/"* /home/container/ || return 1
        msg GREEN "  ✓ Server files installed"
    else
        msg RED "Error: Server folder not found in downloaded files"
        rm -rf "$DOWNLOAD_DIR"
        return 1
    fi

    if [ -f "$DOWNLOAD_DIR/Assets.zip" ]; then
        cp "$DOWNLOAD_DIR/Assets.zip" /home/container/ || return 1
        msg GREEN "  ✓ Assets installed"
    else
        msg YELLOW "Warning: Assets.zip not found in downloaded files"
    fi

    # Save version
    echo "$REMOTE_VERSION" > "/home/container/.version"

    # Cleanup
    rm -rf "$DOWNLOAD_DIR"

    msg GREEN "✓ Hytale server updated to version $REMOTE_VERSION"

    # Clean up entire temp directory after successful installation
    rm -rf /home/container/.tmp

    return 0
}

# Check for game files and handle AUTO_UPDATE
if [ "$AUTO_UPDATE" = "1" ]; then
    msg CYAN "Auto-update enabled, downloading latest version..."
    if download_hytale; then
        msg GREEN "✓ Server ready to start"
    else
        msg RED "Error: Auto-update failed, server will not start"
        exit 1
    fi
else
    # Check for existing game files
    if [ ! -f "/home/container/HytaleServer.jar" ] && [ ! -d "/home/container/Server" ]; then
        msg YELLOW "No Hytale server files found"
        msg CYAN "Set AUTO_UPDATE=1 to automatically download files"

        # Try to check for updates anyway
        check_for_updates || true
    else
        # Check for updates in background when server exists
        check_for_updates || true
    fi
fi

# Function to manage Performance Saver plugin
manage_psaver() {
    # Create mods directory if it doesn't exist
    mkdir -p "$PSAVER_PLUGINS_DIR"

    if [ "$PSAVER" = "1" ]; then
        # PSAVER=1: Install and enable the plugin
        msg BLUE "[plugin] Checking Performance Saver plugin..."

        # Check if a jar matching the pattern exists (enabled)
        EXISTING_JAR=$(find "$PSAVER_PLUGINS_DIR" -maxdepth 1 -type f -name "*.jar" ! -name "*.disabled" 2>/dev/null | grep -i "performance\|psaver\|nitrado" | head -n 1)

        if [ -n "$EXISTING_JAR" ]; then
            msg GREEN "  ✓ Performance Saver already installed and enabled"
            return 0
        fi

        # Check if a disabled version exists
        DISABLED_JAR=$(find "$PSAVER_PLUGINS_DIR" -maxdepth 1 -type f -name "*.jar.disabled" 2>/dev/null | grep -i "performance\|psaver\|nitrado" | head -n 1)

        if [ -n "$DISABLED_JAR" ]; then
            msg BLUE "  Re-enabling Performance Saver..."
            mv "$DISABLED_JAR" "${DISABLED_JAR%.disabled}"
            msg GREEN "  ✓ Performance Saver re-enabled"
            return 0
        fi

        # Download and install the plugin
        msg BLUE "  Downloading Performance Saver plugin..."
        TEMP_PSAVER_DIR="/home/container/.tmp/psaver-install"
        rm -rf "$TEMP_PSAVER_DIR"
        mkdir -p "$TEMP_PSAVER_DIR"

        # Get latest release download URL
        DOWNLOAD_URL=$(wget -q -O - "$PSAVER_RELEASES_URL" 2>/dev/null | grep -oP '"browser_download_url":\s*"\K[^"]*\.jar' | head -n 1)

        if [ -z "$DOWNLOAD_URL" ]; then
            msg RED "Error: Could not fetch Performance Saver plugin release"
            rm -rf "$TEMP_PSAVER_DIR"
            return 1
        fi

        # Extract filename from URL
        PLUGIN_FILENAME=$(basename "$DOWNLOAD_URL")

        if ! wget -O "$TEMP_PSAVER_DIR/$PLUGIN_FILENAME" "$DOWNLOAD_URL" 2>/dev/null; then
            msg RED "Error: Failed to download Performance Saver plugin"
            rm -rf "$TEMP_PSAVER_DIR"
            return 1
        fi

        # Copy to mods directory
        cp "$TEMP_PSAVER_DIR/$PLUGIN_FILENAME" "$PSAVER_PLUGINS_DIR/"
        rm -rf "$TEMP_PSAVER_DIR"
        msg GREEN "  ✓ Performance Saver plugin installed ($PLUGIN_FILENAME)"
        return 0

    else
        # PSAVER=0: Disable the plugin if it exists
        EXISTING_JAR=$(find "$PSAVER_PLUGINS_DIR" -maxdepth 1 -type f -name "*.jar" ! -name "*.disabled" 2>/dev/null | grep -i "performance\|psaver\|nitrado" | head -n 1)

        if [ -n "$EXISTING_JAR" ]; then
            msg BLUE "[plugin] Disabling Performance Saver..."
            JAR_NAME=$(basename "$EXISTING_JAR")
            mv "$EXISTING_JAR" "${EXISTING_JAR}.disabled"
            msg GREEN "  ✓ Performance Saver disabled ($JAR_NAME → $JAR_NAME.disabled)"
        fi
    fi
}

# Manage Performance Saver plugin
if [ "$PSAVER" = "1" ] || [ -n "$(find "$PSAVER_PLUGINS_DIR" -maxdepth 1 -name "*.jar*" -type f 2>/dev/null | head -1)" ]; then
    manage_psaver || true
fi

# Convert all of the "{{VARIABLE}}" parts of the command into the expected shell
# variable format of "${VARIABLE}" before evaluating the string and automatically
# replacing the values.
PARSED=$(echo "${STARTUP}" | sed -e 's/{{/${/g' -e 's/}}/}/g' | eval echo "$(cat -)")

# Display the command we're running in the output, and then execute it with eval
printf "\033[1m\033[33mcontainer~ \033[0m"
echo "$PARSED"
# shellcheck disable=SC2086
exec env ${PARSED}
