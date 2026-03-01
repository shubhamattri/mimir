#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Mimir — Migration / Restore Script
# Restores from a backup created by backup.sh onto a new machine.
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Load .env
if [ -f .env ]; then
    set -a; source .env; set +a
else
    echo "ERROR: .env not found. Copy .env.example to .env and configure for this machine."
    exit 1
fi

BACKUP_DIR="${1:-}"

if [ -z "$BACKUP_DIR" ]; then
    echo "Usage: bash scripts/migrate.sh <backup-directory>"
    echo ""
    echo "Available backups:"
    ls -1d "$PROJECT_DIR/backups"/*/ 2>/dev/null || echo "  No backups found in $PROJECT_DIR/backups/"
    exit 1
fi

if [ ! -d "$BACKUP_DIR" ]; then
    echo "ERROR: Backup directory not found: $BACKUP_DIR"
    exit 1
fi

echo "=== Mimir Migration ==="
echo "From backup: $BACKUP_DIR"
echo "Target: $PROJECT_DIR"
echo ""

# --- 1. Ensure Ollama is running and pull models ---
echo "--- Step 1: Ollama Models ---"
if [ -f "$BACKUP_DIR/ollama-models.txt" ]; then
    while IFS= read -r model; do
        echo "Pulling: $model"
        ollama pull "$model"
    done < "$BACKUP_DIR/ollama-models.txt"
else
    echo "No model list found. Pulling defaults..."
    ollama pull "${CHAT_MODEL:-llama3.1:8b}"
    ollama pull "${EMBEDDING_MODEL:-nomic-embed-text}"
fi

# --- 2. Start Open WebUI ---
echo ""
echo "--- Step 2: Start Open WebUI ---"
docker compose up -d

# Wait for container to be ready
echo "Waiting for Open WebUI container..."
sleep 5

# --- 3. Restore Open WebUI data ---
echo ""
echo "--- Step 3: Restore Open WebUI Data ---"
VOLUME_NAME="mimir_open-webui-data"

if [ -f "$BACKUP_DIR/open-webui-data.tar.gz" ]; then
    # Stop webui to safely restore
    docker compose stop open-webui

    docker run --rm \
        -v "${VOLUME_NAME}:/data" \
        -v "$BACKUP_DIR:/backup" \
        alpine sh -c "cd /data && tar xzf /backup/open-webui-data.tar.gz"

    docker compose start open-webui
    echo "  Open WebUI data: Restored"
else
    echo "  No Open WebUI backup found. Fresh install."
fi

# --- 4. Restore cleaned data ---
echo ""
echo "--- Step 4: Restore Cleaned Data ---"
if [ -f "$BACKUP_DIR/cleaned-data.tar.gz" ]; then
    tar xzf "$BACKUP_DIR/cleaned-data.tar.gz" -C "$PROJECT_DIR/data/"
    echo "  Cleaned data: Restored"
else
    echo "  No cleaned data backup found."
fi

# --- 5. Restore prompts ---
echo ""
echo "--- Step 5: Restore Prompts ---"
if [ -d "$BACKUP_DIR/prompts" ]; then
    cp -r "$BACKUP_DIR/prompts/"* "$PROJECT_DIR/prompts/" 2>/dev/null || true
    echo "  Prompts: Restored"
fi

# --- Done ---
echo ""
echo "=== Migration Complete ==="
echo ""
echo "Open WebUI: http://localhost:${WEBUI_PORT:-3000}"
echo ""
echo "If Knowledge Base is empty, re-upload files from data/cleaned/ in Open WebUI."
