.PHONY: help install dev test test-unit test-integration test-cov test-watch lint format check run clean

help:  ## Show this help
    @awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install:  ## Install dependencies
    uv sync

dev:  ## Install with dev dependencies  
    uv sync --extra dev

test:  ## Run all tests
    uv run pytest tests/

test-unit:  ## Run unit tests only
    uv run pytest tests/ -m "unit or not integration"

test-integration:  ## Run integration tests
    uv run pytest tests/ -m "integration" test_basic.py

test-cov:  ## Run tests with coverage
    uv run pytest tests/ --cov=. --cov-report=html --cov-report=term

test-watch:  ## Run tests in watch mode
    uv run pytest tests/ -f

lint:  ## Run linting
    uv run ruff check .

format:  ## Format code
    uv run ruff format .

check:  ## Run full code quality check
    uv run ruff check .
    uv run ruff format --check .
    uv run pytest tests/ --tb=short

fix:  ## Fix auto-fixable issues
    uv run ruff check --fix .
    uv run ruff format .

run:  ## Run the application
    uv run python src/news_aggregator/main.py

clean:  ## Clean cache files
    find . -type d -name __pycache__ -delete
    find . -type f -name "*.pyc" -delete
    rm -rf .pytest_cache/ .ruff_cache/ .mypy_cache/