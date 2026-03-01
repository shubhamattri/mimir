# Detect bash location (macOS, Linux, fallback)
SHELL := $(shell command -v bash 2>/dev/null || echo /bin/bash)
.PHONY: up down restart logs status clean-whatsapp clean-linkedin clean-all backup setup migrate uninstall

# --- Core ---
up:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f --tail=50

status:
	@echo "=== Ollama ==="
	@curl -s http://localhost:11434/api/tags | python3 -c "import sys,json; d=json.load(sys.stdin); [print(f'  {m[\"name\"]}') for m in d.get('models',[])]" 2>/dev/null || echo "  Not running"
	@echo "=== Open WebUI ==="
	@docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "  Not running"

# --- Data Cleaning ---
clean-whatsapp:
	python3 scripts/clean-whatsapp.py

clean-linkedin:
	python3 scripts/clean-linkedin.py

clean-all: clean-whatsapp clean-linkedin

# --- Operations ---
backup:
	./scripts/backup.sh

setup:
	./scripts/setup.sh

migrate:
	./scripts/migrate.sh

uninstall:
	./scripts/uninstall.sh
