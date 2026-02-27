#!/bin/bash
#
# Grow Tent Monitor - Sync Script
# Synchronizes data from Raspberry Pi to LAMP server
#
# Usage: ./sync_from_pi.sh [options]
#   -v  Verbose mode
#   -n  Dry run (no actual sync)
#   -f  Force sync (ignore lock)
#

set -e

# Configuration - Update these values
PI_USER="matthias"
PI_HOST="grow-tent"  # Or use IP address like 192.168.1.100
PI_DATA_PATH="/home/matthias/grow_tent_automation/data"
LOCAL_DATA_PATH="/var/www/grow-tent/public/data"
SCRIPTS_PATH="/var/www/grow-tent/scripts"
LOG_FILE="/var/log/grow-tent-sync.log"
LOCK_FILE="/tmp/grow-tent-sync.lock"
SQLITE_TEMP="/tmp/grow_tent.db"

# Parse arguments
VERBOSE=false
DRY_RUN=false
FORCE=false

while getopts "vnf" opt; do
    case $opt in
        v) VERBOSE=true ;;
        n) DRY_RUN=true ;;
        f) FORCE=true ;;
        ?) echo "Usage: $0 [-v] [-n] [-f]"; exit 1 ;;
    esac
done

# Logging function
log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$msg" >> "$LOG_FILE"
    if $VERBOSE; then
        echo "$msg"
    fi
}

# Check if already running
if [ -f "$LOCK_FILE" ]; then
    if $FORCE; then
        log "WARNING: Force mode - removing stale lock file"
        rm -f "$LOCK_FILE"
    else
        PID=$(cat "$LOCK_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            log "ERROR: Sync already running (PID: $PID)"
            exit 1
        else
            log "WARNING: Removing stale lock file"
            rm -f "$LOCK_FILE"
        fi
    fi
fi

# Create lock file
echo $$ > "$LOCK_FILE"
trap "rm -f $LOCK_FILE" EXIT

log "Starting sync from $PI_HOST"

# Create directories if they don't exist
mkdir -p "$LOCAL_DATA_PATH/photos"
mkdir -p "$LOCAL_DATA_PATH/timelapse"
mkdir -p "$LOCAL_DATA_PATH/diary"

# Rsync options
RSYNC_OPTS="-avz --progress --delete --timeout=60"
if $DRY_RUN; then
    RSYNC_OPTS="$RSYNC_OPTS --dry-run"
fi

# Sync SQLite database first
log "Syncing database..."
if rsync $RSYNC_OPTS \
    "$PI_USER@$PI_HOST:$PI_DATA_PATH/grow_tent.db" \
    "$SQLITE_TEMP" 2>&1 | while read line; do log "  $line"; done; then
    log "Database synced successfully"
else
    log "ERROR: Failed to sync database"
    exit 1
fi

# Sync photos directory
log "Syncing photos..."
if rsync $RSYNC_OPTS \
    --include='*.jpg' --include='*.jpeg' --include='*.png' --include='*/' \
    --exclude='*' \
    "$PI_USER@$PI_HOST:$PI_DATA_PATH/photos/" \
    "$LOCAL_DATA_PATH/photos/" 2>&1 | while read line; do log "  $line"; done; then
    log "Photos synced successfully"
else
    log "WARNING: Failed to sync some photos"
fi

# Sync timelapse directory
log "Syncing time-lapse files..."
if rsync $RSYNC_OPTS \
    --include='*.mp4' --include='*.webm' --include='*.jpg' --include='*/' \
    --exclude='*' \
    "$PI_USER@$PI_HOST:$PI_DATA_PATH/timelapse/" \
    "$LOCAL_DATA_PATH/timelapse/" 2>&1 | while read line; do log "  $line"; done; then
    log "Time-lapse files synced successfully"
else
    log "WARNING: Failed to sync some time-lapse files"
fi

# Sync diary photos
log "Syncing diary photos..."
if rsync $RSYNC_OPTS \
    --include='*.jpg' --include='*.jpeg' --include='*.png' --include='*/' \
    --exclude='*' \
    "$PI_USER@$PI_HOST:$PI_DATA_PATH/diary/" \
    "$LOCAL_DATA_PATH/diary/" 2>&1 | while read line; do log "  $line"; done; then
    log "Diary photos synced successfully"
else
    log "WARNING: Failed to sync some diary photos"
fi

# Import data to MySQL
if ! $DRY_RUN; then
    log "Importing data to MySQL..."
    if php "$SCRIPTS_PATH/import_data.php" 2>&1 | while read line; do log "  $line"; done; then
        log "Data imported successfully"
    else
        log "ERROR: Failed to import data to MySQL"
        exit 1
    fi
fi

# Calculate sync statistics
PHOTOS_COUNT=$(find "$LOCAL_DATA_PATH/photos" -name '*.jpg' 2>/dev/null | wc -l)
VIDEOS_COUNT=$(find "$LOCAL_DATA_PATH/timelapse" -name '*.mp4' 2>/dev/null | wc -l)

log "Sync completed. Photos: $PHOTOS_COUNT, Videos: $VIDEOS_COUNT"
log "----------------------------------------"

exit 0
