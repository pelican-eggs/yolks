#!/bin/bash

# Default the TZ environment variable to UTC.
TZ=${TZ:-UTC}
export TZ

RED=$(tput setaf 1 2>/dev/null || echo '')
GREEN=$(tput setaf 2 2>/dev/null || echo '')
YELLOW=$(tput setaf 3 2>/dev/null || echo '')
BLUE=$(tput setaf 4 2>/dev/null || echo '')
CYAN=$(tput setaf 6 2>/dev/null || echo '')
NC=$(tput sgr0 2>/dev/null || echo '')

ERROR_LOG="/home/container/install_error.log"

msg() {
    local color="$1"
    shift
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

INTERNAL_IP=$(ip route get 1 | awk '{print $(NF-2);exit}')
export INTERNAL_IP

cd /home/container || exit 1

rm -rf /home/container/.tmp
mkdir -p /home/container/.tmp
DOWNLOADER_URL="https://downloader.hytale.com/hytale-downloader.zip"
DOWNLOADER_BIN="${DOWNLOADER_BIN:-/home/container/hytale-downloader}"
AUTO_UPDATE=${AUTO_UPDATE:-0}
PATCHLINE=${PATCHLINE:-release}
CREDENTIALS_PATH="${CREDENTIALS_PATH:-/home/container/.hytale-downloader-credentials.json}"
DOWNLOADER_ARGS=()
DOWNLOADER_ARGS+=("-credentials-path" "$CREDENTIALS_PATH")

PSAVER=${PSAVER:-0}
PSAVER_RELEASES_URL="https://api.github.com/repos/nitrado/hytale-plugin-performance-saver/releases/latest"
PSAVER_PLUGINS_DIR="/home/container/mods"
PSAVER_JAR_NAME="Nitrado_PerformanceSaver"

VERSION_PATTERN='^[0-9]{4}\.[0-9]{2}\.[0-9]{2}-[a-f0-9]+'
DOWNLOADER_OUTPUT_FILTER="Please visit|Path to credentials file|Authorization code:"

# Cleanup invalid version file (e.g., if it contains auth prompts)
# Expected format: YYYY.MM.DD-<hex>. The hash suffix is intentionally
# allowed to be variable-length, as long as it is non-empty hexadecimal.
if [ -f "/home/container/.version" ]; then
    if ! grep -qE "$VERSION_PATTERN" "/home/container/.version"; then
        msg YELLOW "Warning: Invalid .version content detected; removing file"
        rm -f "/home/container/.version"
    fi
fi

line "CYAN"
msg BLUE "System Information"
line "CYAN"
msg CYAN "Runtime Information:"
java -version 2>&1 | sed "s/^/  /"

ARCH=$(uname -m)
case "$ARCH" in
    x86_64)
        ARCH_DISPLAY="AMD64 (x86_64)"
        ;;
    aarch64)
        ARCH_DISPLAY="ARM64 (aarch64)"
        ;;
    *)
        ARCH_DISPLAY="$ARCH (unknown)"
        ;;
esac
msg CYAN "System Architecture: $ARCH_DISPLAY"

install_downloader() {
    msg YELLOW "[installer] Downloader not found, installing..."

    local TEMP_DIR="/home/container/.tmp/hytale-downloader-install"
    rm -rf "$TEMP_DIR"
    mkdir -p "$TEMP_DIR"

    msg BLUE "[installer] Downloading downloader package..."
    if ! wget -O "$TEMP_DIR/downloader.zip" "$DOWNLOADER_URL"; then
        msg RED "Error: Failed to download Hytale Downloader"
        rm -rf "$TEMP_DIR"
        return 1
    fi

    msg BLUE "[installer] Extracting downloader..."
    if ! unzip -o "$TEMP_DIR/downloader.zip" -d "$TEMP_DIR"; then
        msg RED "Error: Failed to extract Hytale Downloader"
        rm -rf "$TEMP_DIR"
        return 1
    fi

    if [ -f "$TEMP_DIR/hytale-downloader-linux-amd64" ]; then
        cp "$TEMP_DIR/hytale-downloader-linux-amd64" "$DOWNLOADER_BIN"
        chmod +x "$DOWNLOADER_BIN"
        msg GREEN "✓ Hytale Downloader installed successfully"
    else
        msg RED "Error: Downloader binary not found in archive"
        rm -rf "$TEMP_DIR"
        return 1
    fi

    rm -rf "$TEMP_DIR"
    return 0
}

format_expiry() {
    local ts="$1"
    [ -z "$ts" ] || [ "$ts" -le 0 ] 2>/dev/null && echo "unknown" && return
    local now diff h m s
    now=$(date +%s)
    diff=$((ts - now))
    if [ "$diff" -lt 0 ]; then
        diff=0
    fi
    h=$((diff / 3600))
    m=$((diff / 60 % 60))
    s=$((diff % 60))
    local abs
    abs=$(date -d @"$ts" +"%Y-%m-%d %H:%M:%S %Z" 2>/dev/null || echo "$ts")
    printf "%dh %dm %ds (until %s)" "$h" "$m" "$s" "$abs"
}

validate_downloader_credentials() {
    if [ ! -f "$CREDENTIALS_PATH" ]; then
        return 1
    fi

    local expires_at
    expires_at=$(grep -o '"expires_at":[0-9]\+' "$CREDENTIALS_PATH" | cut -d: -f2)

    if [ -z "$expires_at" ] || [ "$expires_at" -le 0 ]; then
        return 1
    fi

    local now
    now=$(date +%s)

    if [ $((expires_at - now)) -gt 0 ]; then
        local remaining
        remaining=$(format_expiry "$expires_at")
        msg GREEN "  ✓ Credentials valid - expires: $remaining"
        return 0
    else
        msg YELLOW "  Downloader credentials expired; removing to force re-auth"
        rm -f "$CREDENTIALS_PATH" 2>/dev/null || true
        return 1
    fi
}

initialize_credentials() {
    if [ ! -f "$CREDENTIALS_PATH" ]; then
        msg BLUE "[auth] Initializing downloader to create credentials (one-time)..."
        "$DOWNLOADER_BIN" -print-version -skip-update-check 2>&1 | sed "s/.*/  ${CYAN}&${NC}/"
        if [ -f "$CREDENTIALS_PATH" ]; then
            msg GREEN "  ✓ Credentials file created"
            if [[ ! " ${DOWNLOADER_ARGS[*]} " =~ " -credentials-path " ]]; then
                DOWNLOADER_ARGS+=("-credentials-path" "$CREDENTIALS_PATH")
            fi
        else
            msg YELLOW "  Note: Credentials file not created yet; continuing without it"
        fi
    fi
}

line "BLUE"
msg  BLUE "Downloader Update Check"
line "BLUE"
if [ -f "$DOWNLOADER_BIN" ]; then
    msg BLUE "[startup] Checking for downloader updates..."

    DOWNLOADER_CHECK_OUTPUT=$("$DOWNLOADER_BIN" "${DOWNLOADER_ARGS[@]}" -check-update 2>&1)
    echo "$DOWNLOADER_CHECK_OUTPUT" | sed "s/.*/  ${CYAN}&${NC}/"

    if echo "$DOWNLOADER_CHECK_OUTPUT" | grep -q "A new version is available"; then
        msg YELLOW "[startup] Downloader update available, downloading..."
        if ! install_downloader; then
            msg RED "Error: Failed to update Hytale Downloader"
        else
            msg GREEN "✓ Hytale Downloader updated successfully"
        fi
    else
        msg GREEN "  ✓ Downloader is up to date"
    fi

    if [ -f "$CREDENTIALS_PATH" ]; then
        msg GREEN "  ✓ Valid downloader auth file found"
    fi
    validate_downloader_credentials || true
fi

check_for_updates() {
    msg BLUE "[update] Checking for Hytale server updates..."

    if [ ! -f "$DOWNLOADER_BIN" ]; then
        if ! install_downloader; then
            msg RED "Error: Failed to install Hytale Downloader"
            return 1
        fi
    fi

    initialize_credentials

    DOWNLOADER_OUTPUT=$(timeout 10 "$DOWNLOADER_BIN" "${DOWNLOADER_ARGS[@]}" -print-version -skip-update-check 2>&1)

    CURRENT_VERSION=$(echo "$DOWNLOADER_OUTPUT" | grep -E "$VERSION_PATTERN" | head -1)
    if [ -z "$CURRENT_VERSION" ]; then
        msg YELLOW "Warning: Could not determine game version"
        echo "$DOWNLOADER_OUTPUT" | sed "s/.*/  ${CYAN}&${NC}/"
        return 1
    fi

    msg GREEN "Current game version: $CURRENT_VERSION"
    return 0
}

download_hytale() {
    msg BLUE "[update] Checking for Hytale updates..."

    if [ ! -f "$DOWNLOADER_BIN" ]; then
        if ! install_downloader; then
            msg RED "Error: Failed to install Hytale Downloader"
            return 1
        fi
    fi

    initialize_credentials

    LOCAL_VERSION=""
    if [ -f "/home/container/.version" ]; then
        LOCAL_VERSION=$(grep -E "$VERSION_PATTERN" -m1 \
            "/home/container/.version" 2>/dev/null)
    fi

    msg CYAN "  Local version: ${LOCAL_VERSION:-none installed}"

    msg BLUE "[update 1/3] Fetching remote version..."
    DOWNLOADER_OUTPUT=$(timeout 10 "$DOWNLOADER_BIN" "${DOWNLOADER_ARGS[@]}" -patchline "$PATCHLINE" -print-version -skip-update-check 2>&1)

    REMOTE_VERSION=$(echo "$DOWNLOADER_OUTPUT" | grep -E "$VERSION_PATTERN" | head -1)
    if [ -z "$REMOTE_VERSION" ]; then
        msg RED "Error: Could not determine remote version"
        echo "$DOWNLOADER_OUTPUT" | sed "s/.*/  ${CYAN}&${NC}/"
        return 1
    fi

    msg CYAN "  Remote version: $REMOTE_VERSION"

    if [ "$LOCAL_VERSION" = "$REMOTE_VERSION" ] && [ -f "/home/container/HytaleServer.jar" ]; then
        msg GREEN "✓ Already running version $REMOTE_VERSION - no update needed"
        return 0
    fi

    msg BLUE "[update 2/3] Downloading Hytale build..."

    DOWNLOAD_DIR="/home/container/.tmp/hytale-download"
    rm -rf "$DOWNLOAD_DIR"
    mkdir -p "$DOWNLOAD_DIR"

    if ! (cd "$DOWNLOAD_DIR" && "$DOWNLOADER_BIN" "${DOWNLOADER_ARGS[@]}" -patchline "$PATCHLINE" -skip-update-check 2>&1 | sed "s/.*/  ${CYAN}&${NC}/"); then
        msg RED "Error: Hytale Downloader failed"
        rm -rf "$DOWNLOAD_DIR"
        return 1
    fi

    GAME_ZIP=$(find "$DOWNLOAD_DIR" -maxdepth 1 -name "*.zip" -type f | head -n 1)

    if [ -z "$GAME_ZIP" ] || [ ! -f "$GAME_ZIP" ]; then
        msg RED "Error: No zip file found in download directory"
        rm -rf "$DOWNLOAD_DIR"
        return 1
    fi

    msg BLUE "[update 3/3] Extracting and installing..."
    if ! unzip -o "$GAME_ZIP" -d "$DOWNLOAD_DIR"; then
        msg RED "Error: Failed to extract Hytale server files"
        rm -rf "$DOWNLOAD_DIR"
        return 1
    fi

    if [ -d "$DOWNLOAD_DIR/Server" ]; then
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

    echo "$REMOTE_VERSION" > "/home/container/.version"
    rm -rf "$DOWNLOAD_DIR"

    msg GREEN "✓ Hytale server updated to version $REMOTE_VERSION"
    rm -rf /home/container/.tmp
    return 0
}

line "BLUE"
msg BLUE "Hytale Gamefiles Update Check"
line "BLUE"
if [ "$AUTO_UPDATE" = "1" ]; then
    msg CYAN "Auto-update enabled, downloading latest version..."
    if ! download_hytale; then
        msg RED "Error: Auto-update failed, server will not start"
        exit 1
    fi
else
    if [ ! -f "/home/container/HytaleServer.jar" ] && [ ! -d "/home/container/Server" ]; then
        msg YELLOW "No Hytale server files found"
        msg CYAN "Set AUTO_UPDATE=1 to automatically download files"

        check_for_updates || true
    else
        check_for_updates || true
    fi
fi

manage_psaver() {
    mkdir -p "$PSAVER_PLUGINS_DIR"

    purge_psaver_duplicates() {
        local kept=""

        if compgen -G "$PSAVER_PLUGINS_DIR/${PSAVER_JAR_NAME}*.jar" >/dev/null; then
            kept=$(ls -1t "$PSAVER_PLUGINS_DIR"/${PSAVER_JAR_NAME}*.jar 2>/dev/null | head -n1)
            ls -1t "$PSAVER_PLUGINS_DIR"/${PSAVER_JAR_NAME}*.jar 2>/dev/null | tail -n +2 | while read -r jar; do
                msg YELLOW "  Removing duplicate $(basename "$jar")"
                rm -f "$jar"
            done
        fi

        if compgen -G "$PSAVER_PLUGINS_DIR/${PSAVER_JAR_NAME}*.jar.disabled" >/dev/null; then
            ls -1 "$PSAVER_PLUGINS_DIR"/${PSAVER_JAR_NAME}*.jar.disabled 2>/dev/null | while read -r jar; do
                msg YELLOW "  Removing disabled copy $(basename "$jar")"
                rm -f "$jar"
            done
        fi

        echo "$kept"
    }

    EXISTING_JAR=$(purge_psaver_duplicates)

    if [ "$PSAVER" = "1" ]; then
        msg BLUE "[plugin] Checking Performance Saver plugin..."

        # If we still have an enabled jar after cleanup, reuse it
        if [ -n "$EXISTING_JAR" ] && [ "${EXISTING_JAR##*.}" = "jar" ]; then
            msg GREEN "  ✓ Performance Saver already installed and enabled"
            return 0
        fi

        msg BLUE "  Downloading Performance Saver plugin..."
        TEMP_PSAVER_DIR="/home/container/.tmp/psaver-install"
        rm -rf "$TEMP_PSAVER_DIR"
        mkdir -p "$TEMP_PSAVER_DIR"

        DOWNLOAD_URL=$(wget -q -O - "$PSAVER_RELEASES_URL" 2>/dev/null | jq -r '.assets[].browser_download_url | select(endswith(".jar"))' | head -n 1)

        if [ -z "$DOWNLOAD_URL" ]; then
            msg RED "Error: Could not fetch Performance Saver plugin release"
            rm -rf "$TEMP_PSAVER_DIR"
            return 1
        fi

        PLUGIN_FILENAME=$(basename "$DOWNLOAD_URL")

        if ! wget -O "$TEMP_PSAVER_DIR/$PLUGIN_FILENAME" "$DOWNLOAD_URL" --ca-certificate=/etc/ssl/certs/ca-certificates.crt 2>/dev/null; then
            msg RED "Error: Failed to download Performance Saver plugin"
            rm -rf "$TEMP_PSAVER_DIR"
            return 1
        fi

        if ! file "$TEMP_PSAVER_DIR/$PLUGIN_FILENAME" | grep -q "Java archive"; then
            msg RED "Error: Downloaded file is not a valid JAR archive"
            rm -rf "$TEMP_PSAVER_DIR"
            return 1
        fi

        # Remove all old versions before installing the freshly downloaded one
        msg BLUE "  Removing old plugin versions..."
        for old_jar in "$PSAVER_PLUGINS_DIR"/${PSAVER_JAR_NAME}*.jar "$PSAVER_PLUGINS_DIR"/${PSAVER_JAR_NAME}*.jar.disabled; do
            if [ -f "$old_jar" ]; then
                msg YELLOW "  Deleting $(basename "$old_jar")"
                rm -f "$old_jar"
            fi
        done

        if ! cp "$TEMP_PSAVER_DIR/$PLUGIN_FILENAME" "$PSAVER_PLUGINS_DIR/"; then
            msg RED "Error: Failed to install Performance Saver plugin (copy failed)"
            rm -rf "$TEMP_PSAVER_DIR"
            return 1
        fi
        rm -rf "$TEMP_PSAVER_DIR"
        msg GREEN "  ✓ Performance Saver plugin installed ($PLUGIN_FILENAME)"
        return 0

    else
        if [ -n "$EXISTING_JAR" ]; then
            msg BLUE "[plugin] Disabling Performance Saver..."
            JAR_NAME=$(basename "$EXISTING_JAR")
            mv "$EXISTING_JAR" "${EXISTING_JAR}.disabled"
            msg GREEN "  ✓ Performance Saver disabled ($JAR_NAME → $JAR_NAME.disabled)"
        fi

        # Ensure the plugin is gone when not requested (prevents leftovers after updates)
        for old_jar in "$PSAVER_PLUGINS_DIR"/${PSAVER_JAR_NAME}*.jar "$PSAVER_PLUGINS_DIR"/${PSAVER_JAR_NAME}*.jar.disabled; do
            if [ -f "$old_jar" ]; then
                rm -f "$old_jar"
            fi
        done
        msg GREEN "  ✓ Performance Saver removed from mods folder"
    fi
}

line "BLUE"
msg BLUE "Plugin Installation"
line "BLUE"
if [ "$PSAVER" = "1" ] || [ -n "$(find "$PSAVER_PLUGINS_DIR" -maxdepth 1 -type f -name "${PSAVER_JAR_NAME}*.jar" ! -name "*.disabled" 2>/dev/null | head -n 1)" ]; then
    manage_psaver || true
fi

line "BLUE"
msg BLUE "Server Authentication Info"
line "BLUE"
msg CYAN "Authentication will be handled by the server itself on first launch."
msg CYAN "Use the in-game command: /auth login device"
msg CYAN "Then follow the instructions to visit: https://accounts.hytale.com/device"
msg CYAN "and enter the code displayed by the server."
line "CYAN"

PARSED=$(echo "${STARTUP}" | sed -e 's/{{/${/g' -e 's/}}/}/g' | eval echo "$(cat -)")

printf "\033[1m\033[33mcontainer~ \033[0m"
echo "$PARSED"
exec env ${PARSED}
