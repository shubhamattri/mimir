#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Mimir — Backup Script
# Backs up: Open WebUI data, cleaned data, prompts, config
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$PROJECT_DIR/backups/$TIMESTAMP"
mkdir -p "$BACKUP_DIR"

echo "=== Mimir Backup ==="
echo "Backup dir: $BACKUP_DIR"

# --- 1. Open WebUI data (Docker volume) ---
echo ""
echo "--- Backing up Open WebUI data ---"
VOLUME_NAME="mimir_open-webui-data"

if docker volume inspect "$VOLUME_NAME" &>/dev/null; then
    docker run --rm \
        -v "${VOLUME_NAME}:/data" \
        -v "$BACKUP_DIR:/backup" \
        alpine tar czf /backup/open-webui-data.tar.gz -C /data .
    echo "  Open WebUI data: OK"
else
    echo "  WARNING: Volume $VOLUME_NAME not found. Skipping."
fi

# --- 2. Cleaned data ---
echo ""
echo "--- Backing up cleaned data ---"
if [ -d "$PROJECT_DIR/data/cleaned" ] && [ "$(ls -A "$PROJECT_DIR/data/cleaned" 2>/dev/null)" ]; then
    tar czf "$BACKUP_DIR/cleaned-data.tar.gz" -C "$PROJECT_DIR/data" cleaned/
    echo "  Cleaned data: OK"
else
    echo "  No cleaned data to backup"
fi

# --- 3. Prompts ---
echo ""
echo "--- Backing up prompts ---"
cp -r "$PROJECT_DIR/prompts" "$BACKUP_DIR/prompts"
echo "  Prompts: OK"

# --- 4. Config ---
echo ""
echo "--- Backing up config ---"
cp "$PROJECT_DIR/.env" "$BACKUP_DIR/env.bak" 2>/dev/null || true
cp "$PROJECT_DIR/docker-compose.yml" "$BACKUP_DIR/docker-compose.yml.bak"
echo "  Config: OK"

# --- 5. Ollama models list (for re-pulling on restore) ---
echo ""
echo "--- Recording Ollama model list ---"
if curl -s http://localhost:11434/api/tags &>/dev/null; then
    curl -s http://localhost:11434/api/tags | python3 -c "
import sys, json
data = json.load(sys.stdin)
for m in data.get('models', []):
    print(m['name'])
" > "$BACKUP_DIR/ollama-models.txt"
    echo "  Model list: OK"
else
    echo "  WARNING: Ollama not running. Model list skipped."
fi

# --- Summary ---
BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
echo ""
echo "=== Backup Complete ==="
echo "Location: $BACKUP_DIR"
echo "Size: $BACKUP_SIZE"
echo ""
echo "To restore: bash scripts/migrate.sh $BACKUP_DIR"
