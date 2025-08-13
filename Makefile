.PHONY: help install dev test lint format check run clean

help:  ## Show this help
    @awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install:  ## Install dependencies
    uv sync

dev:  ## Install with dev dependencies  
    uv sync --extra dev

test:  ## Run tests
    uv run pytest

lint:  ## Run linting
    uv run ruff check .

format:  ## Format code
    uv run ruff format .

check:  ## Run full code quality check
    uv run ruff check .
    uv run ruff format --check .
    uv run mypy src/

fix:  ## Fix auto-fixable issues
    uv run ruff check --fix .
    uv run ruff format .

run:  ## Run the application
    uv run python src/news_aggregator/main.py

clean:  ## Clean cache files
    find . -type d -name __pycache__ -delete
    find . -type f -name "*.pyc" -delete
    rm -rf .pytest_cache/ .ruff_cache/ .mypy_cache/