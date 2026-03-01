# Mimir Roadmap

## Current: Tier 1 — Local Mac (M2 Pro 16GB)

- Ollama (native, Metal GPU) + Open WebUI (Docker)
- **Chat model:** Qwen3 8B (best multilingual + reasoning at 8B)
- **Classifier:** Llama 3.2 3B (fast NSFW filter for data cleaning)
- **Embeddings:** nomic-embed-text
- Built-in RAG via Open WebUI Knowledge Base
- Data: WhatsApp + LinkedIn + docs, sanitized locally

## Planned: Tier 1.5 — VM Deployment (24GB+ RAM)

**Trigger:** When M2 Pro isn't always-on, or need remote access.

- **Upgrade chat model to Kimi K2.5** (1T params MoE, 32B active)
  - Frontier-level reasoning, competes with GPT-5 / Opus 4.6
  - Needs 24GB+ RAM (Oracle Cloud free tier ARM VM = 24GB, free forever)
  - Multimodal (can process images too)
  - `ollama pull kimi-k2.5`
- Same architecture, just change `.env`:
  ```
  CHAT_MODEL=kimi-k2.5
  OLLAMA_BASE_URL=http://localhost:11434  # or Docker internal
  ```
- Add Tailscale/WireGuard for secure remote access
- Consider always-on with systemd service

## Planned: Tier 2 — Custom Ingestion (If RAG Quality Is Poor)

**Trigger:** Open WebUI's built-in chunking isn't good enough.

- Replace built-in RAG with txtai or LlamaIndex
- Semantic chunking (conversation-aware, not fixed-size)
- Keep Open WebUI as chat frontend

## Planned: Tier 3 — API + Bot Integrations

**Trigger:** Need to expose clone via Telegram, WhatsApp, or other apps.

- FastAPI + Qdrant (vector DB)
- Custom retriever with conversation-aware context
- Telegram bot as first consumer
- Open WebUI becomes one of many frontends

## Model Upgrade Path

| Stage | Model | Params (Active) | RAM Needed | Why |
|-------|-------|-----------------|------------|-----|
| **Now** | Qwen3 8B | 8B | ~5GB | Best 8B: multilingual, thinking mode |
| **VM** | Kimi K2.5 | 32B (of 1T MoE) | 24GB+ | Frontier-level, multimodal |
| **Future** | Whatever's best | TBD | TBD | Re-evaluate every 3 months |
