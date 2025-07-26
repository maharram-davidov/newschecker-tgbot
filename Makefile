# NewsChecker Makefile
# Provides common development and deployment tasks

.PHONY: help install install-dev test lint format check clean run-bot run-web run-both docker-build docker-run setup

# Default target
help:
	@echo "NewsChecker Development Commands:"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make setup          - Complete project setup (install + create .env)"
	@echo "  make install        - Install production dependencies"
	@echo "  make install-dev    - Install development dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make test           - Run test suite"
	@echo "  make lint           - Run linting checks"
	@echo "  make format         - Format code with black and isort"
	@echo "  make check          - Run all checks (lint + test)"
	@echo "  make clean          - Clean up temporary files"
	@echo ""
	@echo "Running:"
	@echo "  make run-bot        - Run Telegram bot"
	@echo "  make run-web        - Run web interface"
	@echo "  make run-both       - Run bot and web interface"
	@echo "  make config-check   - Validate configuration"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build   - Build Docker image"
	@echo "  make docker-run     - Run with Docker Compose"
	@echo "  make docker-stop    - Stop Docker containers"

# Installation targets
install:
	pip install -e .

install-dev:
	pip install -e ".[dev,monitoring]"
	pre-commit install || echo "pre-commit not available"

# Setup target
setup: install-dev
	@if [ ! -f .env ]; then \
		echo "Creating .env file from template..."; \
		cp .env.template .env; \
		echo "✅ .env file created. Please edit it with your API keys."; \
	else \
		echo "⚠️  .env file already exists."; \
	fi
	@echo "✅ Setup complete! Don't forget to configure your .env file."

# Testing targets
test:
	python -m pytest tests/ -v --cov=src/newschecker --cov-report=html --cov-report=term

test-fast:
	python -m pytest tests/ -x -v

# Code quality targets
lint:
	python -m flake8 src/ tests/
	python -m mypy src/newschecker/

format:
	python -m black src/ tests/
	python -m isort src/ tests/

check: lint test

# Cleaning targets
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf logs/*.log

# Running targets
run-bot:
	python -m src.newschecker.main bot

run-web:
	python -m src.newschecker.main web

run-both:
	python -m src.newschecker.main both

config-check:
	python -m src.newschecker.main bot --config-check

# Docker targets
docker-build:
	docker-compose build

docker-run:
	docker-compose up -d

docker-stop:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-shell:
	docker-compose exec newschecker-bot bash

# Development server with auto-reload
dev-bot:
	watchdog --patterns="*.py" --recursive --auto-restart -- python -m src.newschecker.main bot

dev-web:
	FLASK_ENV=development python -m src.newschecker.main web

# Database management
db-migrate:
	python -c "from src.newschecker.core.database import db; db._create_tables(); print('Database migration completed')"

db-cleanup:
	python -c "from src.newschecker.core.database import db; db.cleanup_old_data(); print('Database cleanup completed')"

# Monitoring and stats
stats:
	python -c "from src.newschecker.core.database import db; from src.newschecker.core.cache import news_cache; from src.newschecker.utils.rate_limiting import rate_limiter; print('Database stats:', db.get_database_stats()); print('Cache stats:', news_cache.get_stats()); print('Rate limiter stats:', rate_limiter.get_global_stats())"

# Security check
security-check:
	pip-audit
	bandit -r src/

# Package building
build:
	python -m build

# Requirements management
update-deps:
	pip-compile requirements.in
	pip-compile requirements-dev.in

# Git hooks
pre-commit:
	pre-commit run --all-files 