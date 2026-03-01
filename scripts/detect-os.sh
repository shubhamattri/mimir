#!/usr/bin/env bash
# =============================================================================
# Mimir — OS Detection Library
# Source this in any script: source "$(dirname "$0")/detect-os.sh"
# =============================================================================

# --- OS ---
MIMIR_OS="$(uname -s)"    # Darwin, Linux
MIMIR_ARCH="$(uname -m)"  # arm64, x86_64, aarch64

# Normalize arch (Apple Silicon = arm64, Linux ARM = aarch64 → both = arm64)
case "$MIMIR_ARCH" in
    aarch64) MIMIR_ARCH="arm64" ;;
esac

# --- Package manager ---
detect_pkg_manager() {
    if command -v brew &>/dev/null; then
        echo "brew"
    elif command -v apt-get &>/dev/null; then
        echo "apt"
    elif command -v dnf &>/dev/null; then
        echo "dnf"
    elif command -v yum &>/dev/null; then
        echo "yum"
    elif command -v pacman &>/dev/null; then
        echo "pacman"
    elif command -v apk &>/dev/null; then
        echo "apk"
    else
        echo "unknown"
    fi
}
MIMIR_PKG="$(detect_pkg_manager)"

# --- Docker Compose command (v2 vs v1) ---
detect_docker_compose() {
    if docker compose version &>/dev/null 2>&1; then
        echo "docker compose"
    elif command -v docker-compose &>/dev/null; then
        echo "docker-compose"
    else
        echo ""
    fi
}
MIMIR_COMPOSE="$(detect_docker_compose)"

# --- GPU detection ---
detect_gpu() {
    if [ "$MIMIR_OS" = "Darwin" ]; then
        # macOS = always Metal (M-series or Intel with AMD)
        if [[ "$MIMIR_ARCH" = "arm64" ]]; then
            echo "metal"
        else
            echo "none"
        fi
    elif command -v nvidia-smi &>/dev/null 2>&1; then
        echo "nvidia"
    elif [ -d /dev/dri ]; then
        echo "amd"  # ROCm possible
    else
        echo "none"
    fi
}
MIMIR_GPU="$(detect_gpu)"

# --- Ollama optimal install method ---
# macOS: native (Metal GPU). Linux: native or Docker depending on GPU.
detect_ollama_strategy() {
    if [ "$MIMIR_OS" = "Darwin" ]; then
        echo "native"  # Always native on Mac for Metal
    elif [ "$MIMIR_GPU" = "nvidia" ] || [ "$MIMIR_GPU" = "none" ]; then
        echo "native"  # Native works fine on Linux too
    else
        echo "native"
    fi
}
MIMIR_OLLAMA_STRATEGY="$(detect_ollama_strategy)"

# --- Ollama base URL for Docker containers ---
detect_ollama_url() {
    if [ "$MIMIR_OS" = "Darwin" ]; then
        # Docker Desktop on macOS resolves host.docker.internal automatically
        echo "http://host.docker.internal:11434"
    else
        # Linux: host.docker.internal works with extra_hosts in compose
        echo "http://host.docker.internal:11434"
    fi
}
MIMIR_OLLAMA_URL="$(detect_ollama_url)"

# --- Summary (called with --info flag) ---
if [[ "${1:-}" = "--info" ]]; then
    echo "OS:         $MIMIR_OS"
    echo "Arch:       $MIMIR_ARCH"
    echo "Package:    $MIMIR_PKG"
    echo "Compose:    ${MIMIR_COMPOSE:-NOT FOUND}"
    echo "GPU:        $MIMIR_GPU"
    echo "Ollama:     $MIMIR_OLLAMA_STRATEGY"
    echo "Ollama URL: $MIMIR_OLLAMA_URL"
fi
