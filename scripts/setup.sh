#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Mimir — First-Time Setup
# Auto-detects OS, package manager, GPU, and Docker version.
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# --- OS Detection ---
source "$SCRIPT_DIR/detect-os.sh"

echo "=== Mimir Setup ==="
echo "Project:  $PROJECT_DIR"
echo "OS:       $MIMIR_OS ($MIMIR_ARCH)"
echo "GPU:      $MIMIR_GPU"
echo "Package:  $MIMIR_PKG"
echo ""

# --- Load .env ---
if [ -f .env ]; then
    set -a; source .env; set +a
else
    echo "ERROR: .env not found. Copy .env.example to .env and configure it."
    exit 1
fi

# --- Step 1: Install Ollama ---
echo "--- Step 1: Ollama ---"

if command -v ollama &>/dev/null; then
    echo "Ollama already installed: $(ollama --version 2>&1 || echo 'unknown version')"
else
    echo "Installing Ollama..."
    case "$MIMIR_OS" in
        Darwin)
            case "$MIMIR_PKG" in
                brew) brew install ollama ;;
                *)    echo "Install Homebrew first: https://brew.sh"; exit 1 ;;
            esac
            ;;
        Linux)
            curl -fsSL https://ollama.com/install.sh | sh
            ;;
        *)
            echo "ERROR: Unsupported OS: $MIMIR_OS"
            echo "Install Ollama manually: https://ollama.com/download"
            exit 1
            ;;
    esac
fi

# --- Ensure Ollama is running ---
if ! curl -s http://localhost:11434/api/tags &>/dev/null; then
    echo "Starting Ollama..."
    case "$MIMIR_OS" in
        Darwin)
            # Try the macOS app first, fall back to CLI serve
            open -a Ollama 2>/dev/null || (ollama serve &)
            ;;
        Linux)
            # systemd service or manual
            if systemctl is-active --quiet ollama 2>/dev/null; then
                echo "  Ollama service already running"
            elif command -v systemctl &>/dev/null; then
                sudo systemctl start ollama 2>/dev/null || (ollama serve &)
            else
                ollama serve &
            fi
            ;;
    esac
    # Wait for Ollama to be ready
    echo "Waiting for Ollama to start..."
    for i in $(seq 1 15); do
        curl -s http://localhost:11434/api/tags &>/dev/null && break
        [ "$i" -eq 15 ] && { echo "ERROR: Ollama didn't start in 15s"; exit 1; }
        sleep 1
    done
    echo "Ollama is running."
fi

# --- Step 2: Pull models ---
echo ""
echo "--- Step 2: Pull Models ---"

CHAT_MODEL="${CHAT_MODEL:-llama3.1:8b}"
EMBEDDING_MODEL="${EMBEDDING_MODEL:-nomic-embed-text}"

echo "Pulling $CHAT_MODEL (may take a few minutes on first run)..."
ollama pull "$CHAT_MODEL"

echo "Pulling $EMBEDDING_MODEL..."
ollama pull "$EMBEDDING_MODEL"

echo "Models ready:"
ollama list

# --- Step 3: Docker + Open WebUI ---
echo ""
echo "--- Step 3: Open WebUI ---"

if [ -z "$MIMIR_COMPOSE" ]; then
    echo "ERROR: Docker not found."
    case "$MIMIR_OS" in
        Darwin) echo "Install Docker Desktop: https://docker.com/products/docker-desktop" ;;
        Linux)  echo "Install Docker Engine: https://docs.docker.com/engine/install/" ;;
    esac
    exit 1
fi

echo "Using: $MIMIR_COMPOSE"
$MIMIR_COMPOSE up -d

echo ""
echo "Waiting for Open WebUI to be ready..."
for i in $(seq 1 30); do
    if curl -s "http://localhost:${WEBUI_PORT:-3000}" &>/dev/null; then
        echo "Open WebUI is ready!"
        break
    fi
    [ "$i" -eq 30 ] && echo "WARNING: Open WebUI didn't respond in 60s. Check: $MIMIR_COMPOSE logs"
    sleep 2
done

# --- Done ---
echo ""
echo "=== Setup Complete ==="
echo ""
echo "Open WebUI:  http://localhost:${WEBUI_PORT:-3000}"
echo "Ollama API:  http://localhost:11434"
echo ""
echo "Next steps:"
echo "  1. Open http://localhost:${WEBUI_PORT:-3000} and create your admin account"
echo "  2. Export your WhatsApp chats and put .txt files in data/raw/whatsapp/"
echo "  3. Run: make clean-whatsapp"
echo "  4. Upload cleaned files to Open WebUI Knowledge Base"
echo "  5. Create a custom Model with the system prompt from prompts/system_prompt.txt"
