.PHONY: install dev-install lint lint-fix format test clean docker-build docker-run docker-compose

# Python related commands with uv
install:
	uv pip install -e .

dev-install:
	uv pip install -e ".[dev]"

lint:
	ruff check .
	ruff format --check .

lint-fix:
	ruff check --fix .
	ruff format .

format:
	ruff format .

test:
	pytest -v -m 'not integration'

test-unit:
	pytest -v -m unit

test-integration:
	pytest -v -m integration 

test-all:
	pytest -v -o addopts=""

test-coverage:
	pytest --cov=k8s_mcp_server --cov-report=term-missing

clean:
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .coverage htmlcov/ .ruff_cache/ __pycache__/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name '*.egg-info' -exec rm -rf {} +

# Docker related commands
docker-build:
	docker build -t k8s-mcp-server -f deploy/docker/Dockerfile .

docker-run:
	docker run -p 9096:9096 -v ~/.kube:/home/appuser/.kube:ro k8s-mcp-server

docker-compose:
	docker-compose up -d

docker-compose-build:
	docker-compose up --build -d

docker-compose-logs:
	docker-compose logs -f k8s-mcp-server

docker-compose-down:
	docker-compose down

# Multi-architecture build (requires Docker Buildx)
docker-buildx:
	docker buildx create --name mybuilder --use
	docker buildx build --platform linux/amd64,linux/arm64 -t k8s-mcp-server -f deploy/docker/Dockerfile .

# Quick build and run (simple version)
docker-quick:
	docker build -t k8s-mcp-server-simple -f Dockerfile.simple .

docker-quick-run:
	docker run --rm -p 9096:9096 k8s-mcp-server-simple

# One-click build and run script
quick-start:
	./build_and_run.sh

quick-start-proxy:
	SET_PROXY=1 ./build_and_run.sh

# Help
help:
	@echo "Available targets:"
	@echo "  install         - Install the package using uv"
	@echo "  dev-install     - Install the package with development dependencies using uv"
	@echo "  lint            - Run linters (ruff)"
	@echo "  lint-fix        - Run linters with automatic fixes"
	@echo "  format          - Format code with ruff"
	@echo "  test            - Run unit tests only (default)"
	@echo "  test-all        - Run all tests including integration tests"
	@echo "  test-unit       - Run unit tests only"
	@echo "  test-integration - Run integration tests only (requires K8s)"
	@echo "  test-coverage   - Run tests with coverage report"
	@echo "  clean           - Remove build artifacts"
	@echo "  docker-build    - Build Docker image"
	@echo "  docker-run      - Run server in Docker with kubeconfig mounted"
	@echo "  docker-compose  - Run server using Docker Compose"
	@echo "  docker-compose-build - Build and run server using Docker Compose"
	@echo "  docker-compose-logs - View Docker Compose logs"
	@echo "  docker-compose-down - Stop Docker Compose services"
	@echo "  docker-buildx   - Build multi-architecture Docker image"
	@echo "  docker-quick    - Quick build using simplified Dockerfile"
	@echo "  docker-quick-run - Run quick build image temporarily"
	@echo "  quick-start     - One-click build and run with persistence"
	@echo "  quick-start-proxy - One-click build and run with proxy"
