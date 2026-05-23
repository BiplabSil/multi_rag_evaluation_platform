# Makefile for Docker operations

# Default values - override with environment variables
REGISTRY ?=
IMAGE_NAME ?= multi-rag-platform
TAG ?= latest

# AWS settings
AWS_REGION ?= us-east-1

# Docker commands
DOCKER := docker
DOCKER_COMPOSE := docker-compose

# Help target
.PHONY: help
help:
	@echo "Available targets:"
	@echo "  build              - Build Docker image"
	@echo "  build-prod         - Build production Docker image"
	@echo "  push               - Push Docker image to registry"
	@echo "  run                - Run container locally"
	@echo "  run-dev            - Run development stack with docker-compose"
	@echo "  run-prod           - Run production stack with docker-compose"
	@echo "  login-ecr          - Login to AWS ECR"
	@echo "  deploy-ecr         - Build and deploy to AWS ECR"
	@echo "  clean              - Remove Docker images"
	@echo ""
	@echo "Environment variables:"
	@echo "  REGISTRY           - Docker registry (e.g., AWS ECR URI)"
	@echo "  IMAGE_NAME         - Docker image name (default: multi-rag-platform)"
	@echo "  TAG                - Docker tag (default: latest)"
	@echo "  AWS_REGION         - AWS region (default: us-east-1)"

# Build Docker image
.PHONY: build
build:
	$(DOCKER) build -f docker/Dockerfile -t $(IMAGE_NAME):$(TAG) .

# Build production Docker image
.PHONY: build-prod
build-prod:
	$(DOCKER) build -f docker/Dockerfile -t $(REGISTRY)/$(IMAGE_NAME):$(TAG) .

# Push Docker image to registry
.PHONY: push
push:
	@if [ -z "$(REGISTRY)" ]; then \
		echo "REGISTRY is not set. Please set it to your Docker registry."; \
		exit 1; \
	fi
	$(DOCKER) push $(REGISTRY)/$(IMAGE_NAME):$(TAG)

# Run container locally
.PHONY: run
run: build
	$(DOCKER) run -p 8000:8000 --env-file .env $(IMAGE_NAME):$(TAG)

# Run development stack with docker-compose
.PHONY: run-dev
run-dev:
	$(DOCKER_COMPOSE) -f docker/docker-compose.yml up

# Run production stack with docker-compose
.PHONY: run-prod
run-prod:
	@if [ ! -f .env.prod ]; then \
		echo ".env.prod file not found. Please create it from .env.prod.example"; \
		exit 1; \
	fi
	$(DOCKER_COMPOSE) -f docker/docker-compose.prod.yml --env-file .env.prod up -d

# Login to AWS ECR
.PHONY: login-ecr
login-ecr:
	@if [ -z "$(REGISTRY)" ]; then \
		echo "REGISTRY is not set. Please set it to your ECR URI."; \
		exit 1; \
	fi
	@aws ecr get-login-password --region $(AWS_REGION) | $(DOCKER) login --username AWS --password-stdin $(REGISTRY)

# Build and deploy to AWS ECR
.PHONY: deploy-ecr
deploy-ecr: login-ecr build-prod push
	@echo "Successfully deployed $(REGISTRY)/$(IMAGE_NAME):$(TAG) to AWS ECR"

# Clean Docker images
.PHONY: clean
clean:
	$(DOCKER) rmi -f $(IMAGE_NAME):$(TAG) 2>/dev/null || true
	@if [ -n "$(REGISTRY)" ]; then \
		$(DOCKER) rmi -f $(REGISTRY)/$(IMAGE_NAME):$(TAG) 2>/dev/null || true; \
	fi

# Default target
.DEFAULT_GOAL := help