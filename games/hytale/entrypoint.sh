TZ=${TZ:-UTC}
export TZ

RED=$(tput setaf 1 2>/dev/null || echo '')
GREEN=$(tput setaf 2 2>/dev/null || echo '')
YELLOW=$(tput setaf 3 2>/dev/null || echo '')
BLUE=$(tput setaf 4 2>/dev/null || echo '')
CYAN=$(tput setaf 6 2>/dev/null || echo '')
NC=$(tput sgr0 2>/dev/null || echo '')

ERROR_LOG="/home/container/install_error.log"
AUTH_LOG="/home/container/.hytale-auth.log"

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

auth_log() {
    local level="$1"
    shift
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    printf "[%s] [%s] %s\n" "$timestamp" "$level" "$*" >> "$AUTH_LOG"
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

HYTALE_API_AUTH=${HYTALE_API_AUTH:-1}
HYTALE_PROFILE_UUID=${HYTALE_PROFILE_UUID:-}
HYTALE_AUTH_STATE_PATH="${HYTALE_AUTH_STATE_PATH:-/home/container/.hytale-auth.json}"
HYTALE_OAUTH_CLIENT_ID="hytale-server"
HYTALE_OAUTH_SCOPE="openid offline auth:server"
HYTALE_DEVICE_AUTH_URL="https://oauth.accounts.hytale.com/oauth2/device/auth"
HYTALE_TOKEN_URL="https://oauth.accounts.hytale.com/oauth2/token"
HYTALE_PROFILES_URL="https://account-data.hytale.com/my-account/get-profiles"
HYTALE_SESSION_URL="https://sessions.hytale.com/game-session/new"
HYTALE_SESSION_REFRESH_URL="https://sessions.hytale.com/game-session/refresh"
HYTALE_DEVICE_POLL_INTERVAL=5
HYTALE_TOKEN_EXPIRY_BUFFER=300
HYTALE_ACCESS_EXPIRES=0
HYTALE_SESSION_EXPIRES=0

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

    if [ -f "$TEMP_DIR/hytale-downloader" ]; then
        cp "$TEMP_DIR/hytale-downloader" "$DOWNLOADER_BIN"
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
    abs=$(date -u -d @"$ts" +"%Y-%m-%d %H:%M:%SZ" 2>/dev/null || echo "$ts")
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
        auth_log "INFO" "Downloader credentials valid - expires at $(date -u -d @"$expires_at" +"%Y-%m-%d %H:%M:%SZ" 2>/dev/null || echo "$expires_at")"
        return 0
    else
        msg YELLOW "  ⚠ Credentials expired, will be regenerated on next use"
        auth_log "WARN" "Downloader credentials expired at $(date -u -d @"$expires_at" +"%Y-%m-%d %H:%M:%SZ" 2>/dev/null || echo "$expires_at")"
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
    if "$DOWNLOADER_BIN" "${DOWNLOADER_ARGS[@]}" -check-update 2>&1 | sed "s/.*/  ${CYAN}&${NC}/"; then
        if [ -f "$CREDENTIALS_PATH" ]; then
            msg GREEN "  ✓ Valid downloader auth file found"
        fi
        validate_downloader_credentials || true
    else
        msg YELLOW "  Note: Downloader update check completed"
    fi
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

    if [ "$PSAVER" = "1" ]; then
        msg BLUE "[plugin] Checking Performance Saver plugin..."
        EXISTING_JAR=$(find "$PSAVER_PLUGINS_DIR" -maxdepth 1 -type f -name "${PSAVER_JAR_NAME}*.jar" ! -name "*.disabled" 2>/dev/null | head -n 1)

        if [ -n "$EXISTING_JAR" ]; then
            msg GREEN "  ✓ Performance Saver already installed and enabled"
            return 0
        fi

        DISABLED_JAR=$(find "$PSAVER_PLUGINS_DIR" -maxdepth 1 -type f -name "${PSAVER_JAR_NAME}*.jar.disabled" 2>/dev/null | head -n 1)

        if [ -n "$DISABLED_JAR" ]; then
            msg BLUE "  Re-enabling Performance Saver..."
            mv "$DISABLED_JAR" "${DISABLED_JAR%.disabled}"
            msg GREEN "  ✓ Performance Saver re-enabled"
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

        if ! cp "$TEMP_PSAVER_DIR/$PLUGIN_FILENAME" "$PSAVER_PLUGINS_DIR/"; then
            msg RED "Error: Failed to install Performance Saver plugin (copy failed)"
            rm -rf "$TEMP_PSAVER_DIR"
            return 1
        fi
        rm -rf "$TEMP_PSAVER_DIR"
        msg GREEN "  ✓ Performance Saver plugin installed ($PLUGIN_FILENAME)"
        return 0

    else
        EXISTING_JAR=$(find "$PSAVER_PLUGINS_DIR" -maxdepth 1 -type f -name "${PSAVER_JAR_NAME}*.jar" ! -name "*.disabled" 2>/dev/null | head -n 1)

        if [ -n "$EXISTING_JAR" ]; then
            msg BLUE "[plugin] Disabling Performance Saver..."
            JAR_NAME=$(basename "$EXISTING_JAR")
            mv "$EXISTING_JAR" "${EXISTING_JAR}.disabled"
            msg GREEN "  ✓ Performance Saver disabled ($JAR_NAME → $JAR_NAME.disabled)"
        fi
    fi
}

line "BLUE"
msg BLUE "Plugin Installation"
line "BLUE"
if [ "$PSAVER" = "1" ] || [ -n "$(find "$PSAVER_PLUGINS_DIR" -maxdepth 1 -type f -name "${PSAVER_JAR_NAME}*.jar" ! -name "*.disabled" 2>/dev/null | head -n 1)" ]; then
    manage_psaver || true
fi

line "BLUE"
msg BLUE "OAuth & Session Setup"
line "BLUE"

json_field_string() {
    local key="$1"
    sed -n 's/.*"'"${key}"'"[[:space:]]*:[[:space:]]*"\([^"\r\n]*\)".*/\1/p' | head -n1
}

json_field_number() {
    local key="$1"
    sed -n 's/.*"'"${key}"'"[[:space:]]*:[[:space:]]*\([0-9]\+\).*/\1/p' | head -n1
}

json_first_uuid() {
    sed -n 's/.*"uuid"[[:space:]]*:[[:space:]]*"\([0-9a-fA-F-]\+\)".*/\1/p' | head -n1
}

iso_to_epoch() {
    local iso="$1"
    [ -z "$iso" ] && echo 0 && return
    date -d "$iso" +%s 2>/dev/null || echo 0
}

load_auth_state() {
    [ -f "$HYTALE_AUTH_STATE_PATH" ] && . "$HYTALE_AUTH_STATE_PATH"
}

write_auth_state() {
    cat > "$HYTALE_AUTH_STATE_PATH" <<EOF
HYTALE_REFRESH_TOKEN="${HYTALE_REFRESH_TOKEN:-}"
HYTALE_ACCESS_TOKEN="${HYTALE_ACCESS_TOKEN:-}"
HYTALE_ACCESS_EXPIRES=${HYTALE_ACCESS_EXPIRES:-0}
HYTALE_PROFILE_UUID="${HYTALE_PROFILE_UUID:-}"
HYTALE_SESSION_TOKEN="${HYTALE_SESSION_TOKEN:-}"
HYTALE_IDENTITY_TOKEN="${HYTALE_IDENTITY_TOKEN:-}"
HYTALE_SESSION_EXPIRES=${HYTALE_SESSION_EXPIRES:-0}
EOF
}

request_device_code() {
    local resp
    resp=$(curl -s -X POST "$HYTALE_DEVICE_AUTH_URL" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "client_id=$HYTALE_OAUTH_CLIENT_ID" \
        -d "scope=$HYTALE_OAUTH_SCOPE")

    DEVICE_CODE=$(printf '%s' "$resp" | json_field_string "device_code")
    USER_CODE=$(printf '%s' "$resp" | json_field_string "user_code")
    VERIFY_URL=$(printf '%s' "$resp" | json_field_string "verification_uri_complete")
    POLL_INTERVAL=$(printf '%s' "$resp" | json_field_number "interval")
    if [ -z "$POLL_INTERVAL" ]; then
        POLL_INTERVAL=$HYTALE_DEVICE_POLL_INTERVAL
    fi

    if [ -z "$DEVICE_CODE" ] || [ -z "$USER_CODE" ] || [ -z "$VERIFY_URL" ]; then
        msg RED "[auth] Failed to request device code"
        auth_log "ERROR" "Failed to request device code"
        return 1
    fi
    auth_log "INFO" "Device code requested successfully"
    msg CYAN "  Visit: $VERIFY_URL"
    msg CYAN "  Code : $USER_CODE"
    return 0
}

poll_for_tokens() {
    local poll_resp
    while true; do
        poll_resp=$(curl -s -X POST "$HYTALE_TOKEN_URL" \
            -H "Content-Type: application/x-www-form-urlencoded" \
            -d "client_id=$HYTALE_OAUTH_CLIENT_ID" \
            -d "grant_type=urn:ietf:params:oauth:grant-type:device_code" \
            -d "device_code=$DEVICE_CODE")

        local error
        error=$(printf '%s' "$poll_resp" | json_field_string "error")
        if [ -n "$error" ]; then
            if [ "$error" = "authorization_pending" ]; then
                sleep "$POLL_INTERVAL"
                continue
            fi
            if [ "$error" = "slow_down" ]; then
                sleep $((POLL_INTERVAL + 5))
                continue
            fi
            msg RED "[auth] Token polling failed: $error"
            return 1
        fi

        HYTALE_ACCESS_TOKEN=$(printf '%s' "$poll_resp" | json_field_string "access_token")
        HYTALE_REFRESH_TOKEN=$(printf '%s' "$poll_resp" | json_field_string "refresh_token")
        local expires_in
        expires_in=$(printf '%s' "$poll_resp" | json_field_number "expires_in")
        local now
        now=$(date +%s)
        HYTALE_ACCESS_EXPIRES=$((now + expires_in))
        auth_log "INFO" "Tokens acquired via device code flow"
        return 0
    done
}

refresh_access_token() {
    local resp
    resp=$(curl -s -X POST "$HYTALE_TOKEN_URL" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "client_id=$HYTALE_OAUTH_CLIENT_ID" \
        -d "grant_type=refresh_token" \
        -d "refresh_token=$HYTALE_REFRESH_TOKEN")

    local new_access
    new_access=$(printf '%s' "$resp" | json_field_string "access_token")
    if [ -z "$new_access" ]; then
        msg RED "[auth] Failed to refresh OAuth token"
        auth_log "ERROR" "Failed to refresh OAuth token"
        return 1
    fi

    HYTALE_ACCESS_TOKEN="$new_access"
    HYTALE_REFRESH_TOKEN=$(printf '%s' "$resp" | json_field_string "refresh_token")
    local expires_in now
    expires_in=$(printf '%s' "$resp" | json_field_number "expires_in")
    now=$(date +%s)
    HYTALE_ACCESS_EXPIRES=$((now + expires_in))
    msg GREEN "[auth] OAuth token refreshed"
    auth_log "INFO" "OAuth token refreshed"
    return 0
}

fetch_profile_uuid() {
    local profiles_resp
    profiles_resp=$(curl -s -X GET "$HYTALE_PROFILES_URL" \
        -H "Authorization: Bearer $HYTALE_ACCESS_TOKEN")

    if [ -z "$profiles_resp" ]; then
        msg RED "[auth] Failed to fetch profiles"
        auth_log "ERROR" "Failed to fetch profiles"
        return 1
    fi

    auth_log "INFO" "Profiles response: $profiles_resp"

    if [ -n "$HYTALE_PROFILE_UUID" ]; then
        auth_log "INFO" "Using pre-configured profile UUID"
        return 0
    fi

    auth_log "DEBUG" "Profiles API response: $profiles_resp"

    HYTALE_PROFILE_UUID=$(printf '%s' "$profiles_resp" | json_first_uuid)

    if [ -z "$HYTALE_PROFILE_UUID" ]; then
        msg RED "[auth] No profile UUID found"
        auth_log "ERROR" "No profile UUID found in profiles response"
        return 1
    fi

    auth_log "INFO" "Profile UUID fetched: $HYTALE_PROFILE_UUID"
    return 0
}

create_game_session() {
    local session_resp
    session_resp=$(curl -s -X POST "$HYTALE_SESSION_URL" \
        -H "Authorization: Bearer $HYTALE_ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"uuid":"'"$HYTALE_PROFILE_UUID"'"}')

    if [ -z "$session_resp" ]; then
        msg RED "[auth] Failed to create game session - empty response"
        auth_log "ERROR" "Failed to create game session - empty response"
        return 1
    fi

    auth_log "DEBUG" "Session API response: $session_resp"

    HYTALE_SESSION_TOKEN=$(printf '%s' "$session_resp" | json_field_string "sessionToken")
    HYTALE_IDENTITY_TOKEN=$(printf '%s' "$session_resp" | json_field_string "identityToken")

    if [ -z "$HYTALE_SESSION_TOKEN" ] || [ -z "$HYTALE_IDENTITY_TOKEN" ]; then
        msg RED "[auth] Failed to create game session"
        auth_log "ERROR" "Failed to create game session"
        return 1
    fi

    local expires_at
    expires_at=$(printf '%s' "$session_resp" | json_field_string "expiresAt")
    if [ -n "$expires_at" ]; then
        HYTALE_SESSION_EXPIRES=$(iso_to_epoch "$expires_at")
        msg GREEN "[auth] Game session created (expires at $expires_at)"
        auth_log "INFO" "Game session created (expires at $expires_at)"
    else
        msg GREEN "[auth] Game session created"
        auth_log "INFO" "Game session created successfully"
        HYTALE_SESSION_EXPIRES=$(($(date +%s) + 3600))
    fi
    return 0

}


refresh_game_session() {
    if [ -z "$HYTALE_SESSION_TOKEN" ]; then
        return 1
    fi

    local resp
    resp=$(curl -s -X POST "$HYTALE_SESSION_REFRESH_URL" \
        -H "Authorization: Bearer $HYTALE_SESSION_TOKEN")

    if [ -z "$resp" ]; then
        msg RED "[auth] Failed to refresh game session - empty response"
        auth_log "ERROR" "Failed to refresh game session - empty response"
        return 1
    fi

    auth_log "DEBUG" "Refresh Session API response: $resp"

    local new_session
    new_session=$(printf '%s' "$resp" | json_field_string "sessionToken")
    if [ -n "$new_session" ]; then
        HYTALE_SESSION_TOKEN="$new_session"
    fi
    local new_identity
    new_identity=$(printf '%s' "$resp" | json_field_string "identityToken")
    if [ -n "$new_identity" ]; then
        HYTALE_IDENTITY_TOKEN="$new_identity"
    fi

    if [ -z "$HYTALE_SESSION_TOKEN" ] || [ -z "$HYTALE_IDENTITY_TOKEN" ]; then
        msg RED "[auth] Failed to refresh game session"
        auth_log "ERROR" "Failed to refresh game session"
        return 1
    fi

    local expires_at
    expires_at=$(printf '%s' "$resp" | json_field_string "expiresAt")
    if [ -n "$expires_at" ]; then
        HYTALE_SESSION_EXPIRES=$(iso_to_epoch "$expires_at")
        msg GREEN "[auth] Game session refreshed (expires at $expires_at)"
        auth_log "INFO" "Game session refreshed (expires at $expires_at)"
    else
        msg GREEN "[auth] Game session refreshed"
        auth_log "INFO" "Game session refreshed successfully"
        HYTALE_SESSION_EXPIRES=$(($(date +%s) + 3600))
    fi
    return 0
}

ensure_oauth_tokens() {
    local now
    now=$(date +%s)

    if [ -n "$HYTALE_ACCESS_TOKEN" ] && [ -n "$HYTALE_ACCESS_EXPIRES" ] && [ $((HYTALE_ACCESS_EXPIRES - HYTALE_TOKEN_EXPIRY_BUFFER)) -gt "$now" ]; then
        return 0
    fi

    if [ -n "$HYTALE_REFRESH_TOKEN" ]; then
        if refresh_access_token; then
            return 0
        fi
        msg YELLOW "[auth] Refresh token invalid, starting new device flow"
    fi

    if ! request_device_code; then
        return 1
    fi
    if ! poll_for_tokens; then
        return 1
    fi
    return 0
}

ensure_session_tokens() {
    local now
    now=$(date +%s)

    if [ -n "$HYTALE_SESSION_TOKEN" ] && [ -n "$HYTALE_SESSION_EXPIRES" ] && [ $((HYTALE_SESSION_EXPIRES - HYTALE_TOKEN_EXPIRY_BUFFER)) -gt "$now" ]; then
        return 0
    fi

    if [ -n "$HYTALE_SESSION_TOKEN" ] && [ $((HYTALE_SESSION_EXPIRES - HYTALE_TOKEN_EXPIRY_BUFFER)) -le "$now" ]; then
        if refresh_game_session; then
            return 0
        fi
        msg YELLOW "[auth] Session refresh failed, creating new session"
    fi

    if ! fetch_profile_uuid; then
        return 1
    fi

    if ! create_game_session; then
        return 1
    fi

    return 0
}

run_hytale_api_auth() {
    [ "$HYTALE_API_AUTH" != "1" ] && return 0

    msg BLUE "[auth] Hytale API authentication enabled"
    auth_log "INFO" "Starting Hytale API authentication"

    load_auth_state

    if ! ensure_oauth_tokens; then
        msg RED "[auth] OAuth acquisition failed"
        auth_log "ERROR" "OAuth acquisition failed"
        return 1
    fi

    if ! ensure_session_tokens; then
        msg RED "[auth] Session acquisition failed"
        auth_log "ERROR" "Session acquisition failed"
        return 1
    fi

    export HYTALE_REFRESH_TOKEN
    export HYTALE_ACCESS_TOKEN
    export HYTALE_ACCESS_EXPIRES
    export HYTALE_SESSION_TOKEN
    export HYTALE_IDENTITY_TOKEN
    export HYTALE_SESSION_EXPIRES
    export HYTALE_PROFILE_UUID

    export HYTALE_SERVER_SESSION_TOKEN="$HYTALE_SESSION_TOKEN"
    export HYTALE_SERVER_IDENTITY_TOKEN="$HYTALE_IDENTITY_TOKEN"

    write_auth_state

    msg GREEN "[auth] Tokens ready and exported"
    msg CYAN "  Access token valid: $(format_expiry "$HYTALE_ACCESS_EXPIRES")"
    msg CYAN "  Session token valid: $(format_expiry "$HYTALE_SESSION_EXPIRES")"
    auth_log "INFO" "Authentication successful - tokens exported"

    msg BLUE "Server Ready for Startup"
    line "CYAN"
    return 0
}

if ! run_hytale_api_auth; then
    msg YELLOW "[auth] Continuing without API-acquired tokens"
fi

PARSED=$(echo "${STARTUP}" | sed -e 's/{{/${/g' -e 's/}}/}/g' | eval echo "$(cat -)")

printf "\033[1m\033[33mcontainer~ \033[0m"
echo "$PARSED"
exec env ${PARSED}
