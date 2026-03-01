#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Mimir — One-Click Uninstall
# Removes: containers, volumes, images, cleaned data, Ollama models (optional)
# Does NOT remove: raw data (your exports), the project folder itself
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

source "$SCRIPT_DIR/detect-os.sh"

echo "=== Mimir Uninstall ==="
echo "OS: $MIMIR_OS ($MIMIR_ARCH)"
echo ""
echo "This will remove:"
echo "  - Docker container + volume (Open WebUI + all knowledge bases)"
echo "  - Cleaned data files"
echo "  - Docker image"
echo ""
echo "This will NOT remove:"
echo "  - Your raw exports (data/raw/)"
echo "  - This project folder"
echo "  - Ollama itself (unless you choose to)"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# --- 1. Stop and remove containers + volumes ---
echo ""
echo "--- Removing Docker containers + volumes ---"
if [ -n "$MIMIR_COMPOSE" ]; then
    $MIMIR_COMPOSE down -v 2>/dev/null && echo "  Done" || echo "  Nothing to remove"
else
    echo "  Docker not found. Skipping."
fi

# --- 2. Remove Docker image ---
echo ""
echo "--- Removing Docker image ---"
docker rmi ghcr.io/open-webui/open-webui:main 2>/dev/null && echo "  Done" || echo "  Image not found or Docker not available"

# --- 3. Remove cleaned data ---
echo ""
echo "--- Removing cleaned data ---"
if [ -d "$PROJECT_DIR/data/cleaned" ]; then
    rm -rf "$PROJECT_DIR/data/cleaned"/*
    echo "  Cleaned data removed (raw exports preserved)"
else
    echo "  No cleaned data found"
fi

# --- 4. Remove backups ---
if [ -d "$PROJECT_DIR/backups" ]; then
    read -p "Remove backups too? (y/N) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$PROJECT_DIR/backups"
        echo "  Backups removed"
    else
        echo "  Backups kept"
    fi
fi

# --- 5. Ollama models (optional) ---
echo ""
read -p "Remove Ollama models (llama3.1:8b + nomic-embed-text)? (y/N) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    ollama rm llama3.1:8b 2>/dev/null && echo "  Removed llama3.1:8b" || echo "  llama3.1:8b not found"
    ollama rm nomic-embed-text 2>/dev/null && echo "  Removed nomic-embed-text" || echo "  nomic-embed-text not found"

    read -p "Uninstall Ollama completely? (y/N) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        case "$MIMIR_OS" in
            Darwin)
                case "$MIMIR_PKG" in
                    brew) brew uninstall ollama 2>/dev/null && echo "  Ollama uninstalled" || echo "  Not installed via brew" ;;
                    *)    echo "  Remove Ollama.app from /Applications manually" ;;
                esac
                ;;
            Linux)
                if command -v systemctl &>/dev/null; then
                    sudo systemctl stop ollama 2>/dev/null || true
                    sudo systemctl disable ollama 2>/dev/null || true
                fi
                sudo rm -f /usr/local/bin/ollama 2>/dev/null || true
                sudo rm -rf /usr/share/ollama 2>/dev/null || true
                sudo userdel ollama 2>/dev/null || true
                sudo groupdel ollama 2>/dev/null || true
                echo "  Ollama uninstalled"
                ;;
        esac
    fi
else
    echo "  Ollama models kept"
fi

echo ""
echo "=== Mimir Uninstalled ==="
echo ""
echo "Your raw exports are still at: $PROJECT_DIR/data/raw/"
echo "To fully remove the project: rm -rf $PROJECT_DIR"
