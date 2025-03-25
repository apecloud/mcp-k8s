.PHONY: install dev-install lint test clean docker-build docker-run docker-compose

# Python related commands
install:
	pip install -e .

dev-install:
	pip install -e ".[dev]"

lint:
	ruff check .
	ruff format --check .

test:
	pytest -v

test-coverage:
	pytest --cov=k8s_mcp_server

clean:
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .coverage htmlcov/ .ruff_cache/ __pycache__/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name '*.egg-info' -exec rm -rf {} +

# Docker related commands
docker-build:
	docker build -t k8s-mcp-server -f deploy/docker/Dockerfile .

docker-run:
	docker run -p 8080:8080 -v ~/.kube:/home/appuser/.kube:ro k8s-mcp-server

docker-compose:
	docker-compose -f deploy/docker/docker-compose.yml up -d

docker-compose-down:
	docker-compose -f deploy/docker/docker-compose.yml down

# Multi-architecture build (requires Docker Buildx)
docker-buildx:
	docker buildx create --name mybuilder --use
	docker buildx build --platform linux/amd64,linux/arm64 -t yourusername/k8s-mcp-server:latest -f deploy/docker/Dockerfile .

# Help
help:
	@echo "Available targets:"
	@echo "  install         - Install the package"
	@echo "  dev-install     - Install the package with development dependencies"
	@echo "  lint            - Run linters"
	@echo "  test            - Run unit tests"
	@echo "  test-coverage   - Run tests with coverage"
	@echo "  clean           - Remove build artifacts"
	@echo "  docker-build    - Build Docker image"
	@echo "  docker-run      - Run server in Docker with kubeconfig mounted"
	@echo "  docker-compose  - Run server using Docker Compose"
	@echo "  docker-compose-down - Stop Docker Compose services"
	@echo "  docker-buildx   - Build multi-architecture Docker image"
