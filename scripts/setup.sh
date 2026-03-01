#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Mimir — First-Time Setup
# Works on macOS (native Ollama) and Linux (Docker Ollama)
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Load .env
if [ -f .env ]; then
    set -a; source .env; set +a
else
    echo "ERROR: .env not found. Copy .env.example to .env and configure it."
    exit 1
fi

echo "=== Mimir Setup ==="
echo "Project dir: $PROJECT_DIR"

# --- Step 1: Ollama ---
echo ""
echo "--- Step 1: Ollama ---"

if command -v ollama &>/dev/null; then
    echo "Ollama already installed: $(ollama --version)"
else
    OS="$(uname -s)"
    if [ "$OS" = "Darwin" ]; then
        echo "Installing Ollama via Homebrew..."
        brew install ollama
    elif [ "$OS" = "Linux" ]; then
        echo "Installing Ollama via official script..."
        curl -fsSL https://ollama.com/install.sh | sh
    else
        echo "ERROR: Unsupported OS: $OS. Install Ollama manually."
        exit 1
    fi
fi

# Ensure Ollama is running
if ! curl -s http://localhost:11434/api/tags &>/dev/null; then
    echo "Starting Ollama..."
    if [ "$(uname -s)" = "Darwin" ]; then
        open -a Ollama || ollama serve &
        sleep 3
    else
        ollama serve &
        sleep 3
    fi
fi

# --- Step 2: Pull models ---
echo ""
echo "--- Step 2: Pull Models ---"

CHAT_MODEL="${CHAT_MODEL:-llama3.1:8b}"
EMBEDDING_MODEL="${EMBEDDING_MODEL:-nomic-embed-text}"

echo "Pulling $CHAT_MODEL (this may take a few minutes on first run)..."
ollama pull "$CHAT_MODEL"

echo "Pulling $EMBEDDING_MODEL..."
ollama pull "$EMBEDDING_MODEL"

echo "Models ready:"
ollama list

# --- Step 3: Docker / Open WebUI ---
echo ""
echo "--- Step 3: Open WebUI ---"

if ! command -v docker &>/dev/null; then
    echo "ERROR: Docker not found. Install Docker Desktop (macOS) or Docker Engine (Linux)."
    exit 1
fi

echo "Starting Open WebUI..."
docker compose up -d

echo ""
echo "Waiting for Open WebUI to be ready..."
for i in $(seq 1 30); do
    if curl -s "http://localhost:${WEBUI_PORT:-3000}" &>/dev/null; then
        echo "Open WebUI is ready!"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "WARNING: Open WebUI didn't respond in 30s. Check: docker compose logs"
    fi
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
