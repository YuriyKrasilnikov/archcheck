.PHONY: help install dev-setup test test-unit test-integration lint format type-check check clean build publish benchmark

help:
	@echo "archcheck development commands:"
	@echo ""
	@echo "Setup:"
	@echo "  make install       - Setup development environment with uv"
	@echo "  make dev-setup     - Full development setup (install + pre-commit)"
	@echo ""
	@echo "Testing:"
	@echo "  make test          - Run all tests with coverage"
	@echo "  make test-unit     - Run unit tests only"
	@echo "  make test-integration - Run integration tests"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint          - Run linters (ruff check + mypy)"
	@echo "  make format        - Format code with ruff"
	@echo "  make type-check    - Run mypy type checking"
	@echo "  make check         - Run all checks (lint + type-check + test)"
	@echo ""
	@echo "Build & Publish:"
	@echo "  make clean         - Remove build artifacts"
	@echo "  make build         - Build wheel and sdist"
	@echo "  make publish       - Publish to PyPI"
	@echo ""
	@echo "Performance:"
	@echo "  make benchmark     - Run performance benchmarks"

install:
	@echo "Installing archcheck in development mode..."
	uv sync --all-groups
	@echo "Done! Run commands with: uv run <command>"

dev-setup: install
	@echo "Setting up pre-commit hooks..."
	uv run pre-commit install
	@echo "Full development setup complete!"

test:
	@echo "Running all tests with coverage..."
	uv run pytest \
		--cov=archcheck \
		--cov-report=html \
		--cov-report=term \
		--cov-report=xml \
		-v

test-unit:
	@echo "Running unit tests..."
	uv run pytest tests/unit/ -v

test-integration:
	@echo "Running integration tests..."
	uv run pytest tests/integration/ -v

lint:
	@echo "Running ruff check..."
	uv run ruff check .
	@echo "Running mypy..."
	uv run mypy src/archcheck

format:
	@echo "Formatting code with ruff..."
	uv run ruff format .
	@echo "Fixing auto-fixable issues..."
	uv run ruff check . --fix

type-check:
	@echo "Running mypy type checker..."
	uv run mypy src/archcheck

check: lint type-check test
	@echo "All checks passed!"

clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/ dist/ *.egg-info htmlcov/ .coverage .pytest_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleanup complete!"

build: clean
	@echo "Building package..."
	uv build
	@echo "Build complete! Check dist/ directory"

publish: build
	@echo "Publishing to PyPI..."
	uvx twine check dist/*
	uvx twine upload dist/*
	@echo "Published to PyPI!"

benchmark:
	@echo "Running performance benchmarks..."
	uv run python scripts/benchmark.py --output benchmark-results.json
