.PHONY: help start-openfga stop-openfga status-openfga logs-openfga import-openfga-store

OPENFGA_API_URL ?= http://localhost:8080
OPENFGA_STORE_FILE ?= ./demo/fga/store.fga.yaml
ENV_FILE ?= .env

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

start-openfga: ## Start OpenFGA in Docker
	@echo "Starting OpenFGA..."
	@docker run -d \
		--name openfga \
		-p 8080:8080 \
		-p 8081:8081 \
		-p 3000:3000 \
		openfga/openfga:latest \
		run
	@echo "OpenFGA started on:"
	@echo "  - HTTP API: http://localhost:8080"
	@echo "  - gRPC API: localhost:8081"
	@echo "  - Playground: http://localhost:3000"

stop-openfga: ## Stop and remove OpenFGA container
	@echo "Stopping OpenFGA..."
	@docker stop openfga 2>/dev/null || true
	@docker rm openfga 2>/dev/null || true
	@echo "OpenFGA stopped"

restart-openfga: stop-openfga start-openfga ## Restart OpenFGA

status-openfga: ## Check OpenFGA container status
	@docker ps -a --filter name=openfga --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

logs-openfga: ## Show OpenFGA logs
	@docker logs -f openfga

import-openfga-store: ## Import OpenFGA store and update env file
	@echo "Importing OpenFGA store..."
	@OUTPUT=$$(fga store import --file $(OPENFGA_STORE_FILE) --api-url $(OPENFGA_API_URL) 2>&1 | head -n1); \
	if [ -z "$$OUTPUT" ]; then \
		echo "Error: Failed to import store"; \
		exit 1; \
	fi; \
	STORE_ID=$$(echo $$OUTPUT | grep -o '"id":"[^"]*"' | head -n1 | cut -d'"' -f4); \
	MODEL_ID=$$(echo $$OUTPUT | grep -o '"authorization_model_id":"[^"]*"' | cut -d'"' -f4); \
	if [ -z "$$STORE_ID" ] || [ -z "$$MODEL_ID" ]; then \
		echo "Error: Failed to extract store ID or model ID"; \
		echo "Output: $$OUTPUT"; \
		exit 1; \
	fi; \
	echo "# OpenFGA Configuration" > $(ENV_FILE); \
	echo "OPENFGA_API_URL=$(OPENFGA_API_URL)" >> $(ENV_FILE); \
	echo "OPENFGA_STORE_ID=$$STORE_ID" >> $(ENV_FILE); \
	echo "OPENFGA_AUTHORIZATION_MODEL_ID=$$MODEL_ID" >> $(ENV_FILE); \
	echo ""; \
	echo "✓ Store imported successfully!"; \
	echo "  Store ID: $$STORE_ID"; \
	echo "  Model ID: $$MODEL_ID"; \
	echo "  Configuration saved to: $(ENV_FILE)"; \
	echo "";

# Development helpers
dev-setup: start-openfga ## Start all required services for development
	@echo "Waiting for OpenFGA to be ready..."
	@sleep 2
	@$(MAKE) import-openfga-store
	@python initdb.py
	@echo ""
	@echo "✓ Development environment ready!"
	@echo "  - OpenFGA: http://localhost:8080"
	@echo "  - Playground: http://localhost:3000/playground"

dev-teardown: stop-openfga ## Stop all development services
	@rm db.sqlite3 || true

run-workflows:
	dapr run --app-id demo \
		--dapr-grpc-port 50001 \
		--dapr-http-port 3500 \
		--resources-path ./resources \
		-- python workflows.py
