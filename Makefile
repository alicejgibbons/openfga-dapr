.PHONY: help start-openfga stop-openfga status-openfga logs-openfga clean-openfga import-openfga-store start-service stop-service restart-service status-service logs-service test test-dual-write

OPENFGA_API_URL ?= http://localhost:8080
OPENFGA_STORE_FILE ?= ./app/fga/store.fga.yaml
ENV_FILE ?= .env
SERVICE_PORT ?= 8000

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

clean-openfga: stop-openfga ## Stop OpenFGA and clean up volumes
	@echo "Cleaning up OpenFGA data..."
	@docker volume prune -f
	@echo "OpenFGA cleaned up"

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

# Service management
start-service: ## Start the FastAPI service
	@echo "Starting FastAPI service..."
	@if [ ! -d ".venv" ]; then \
		echo "Error: Virtual environment not found. Please create it first."; \
		exit 1; \
	fi
	@if pgrep -f "uvicorn app.main:app" > /dev/null; then \
		echo "Service is already running"; \
	else \
		source .venv/bin/activate && \
		nohup uvicorn app.main:app --host 0.0.0.0 --port $(SERVICE_PORT) > service.log 2>&1 & \
		echo $$! > service.pid; \
		sleep 2; \
		if pgrep -f "uvicorn app.main:app" > /dev/null; then \
			echo "✓ Service started on http://localhost:$(SERVICE_PORT)"; \
			echo "  - API Docs: http://localhost:$(SERVICE_PORT)/docs"; \
			echo "  - Logs: tail -f service.log"; \
		else \
			echo "✗ Failed to start service. Check service.log for errors."; \
			exit 1; \
		fi; \
	fi

stop-service: ## Stop the FastAPI service
	@echo "Stopping FastAPI service..."
	@if [ -f service.pid ]; then \
		kill $$(cat service.pid) 2>/dev/null || true; \
		rm -f service.pid; \
	fi
	@pkill -f "uvicorn app.main:app" 2>/dev/null || true
	@echo "Service stopped"

restart-service: stop-service start-service ## Restart the FastAPI service

status-service: ## Check FastAPI service status
	@if pgrep -f "uvicorn app.main:app" > /dev/null; then \
		echo "Service is running on http://localhost:$(SERVICE_PORT)"; \
		ps aux | grep "uvicorn app.main:app" | grep -v grep; \
	else \
		echo "Service is not running"; \
	fi

logs-service: ## Show FastAPI service logs
	@if [ -f service.log ]; then \
		tail -f service.log; \
	else \
		echo "No log file found. Service may not be running."; \
	fi

# Testing
test: ## Run the basic API test script
	@source .venv/bin/activate && python test_api.py

test-dual-write: ## Run the dual write demonstration test
	@source .venv/bin/activate && python test_dual_write.py

# Development helpers
dev-setup: start-openfga ## Start all required services for development
	@echo "Waiting for OpenFGA to be ready..."
	@sleep 2
	@$(MAKE) import-openfga-store
	@$(MAKE) start-service
	@echo ""
	@echo "✓ Development environment ready!"
	@echo "  - FastAPI: http://localhost:$(SERVICE_PORT)"
	@echo "  - API Docs: http://localhost:$(SERVICE_PORT)/docs"
	@echo "  - OpenFGA: http://localhost:8080"
	@echo "  - Playground: http://localhost:3000/playground"

dev-teardown: stop-service stop-openfga ## Stop all development services
	@echo "Development environment stopped"
