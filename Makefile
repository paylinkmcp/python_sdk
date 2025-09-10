# PayLink Python SDK Makefile

.PHONY: help build test publish patch minor major dry-run clean install dev

# Default target
help:
	@echo "PayLink Python SDK - Available Commands"
	@echo "========================================"
	@echo ""
	@echo "Development:"
	@echo "  install     Install the package in development mode"
	@echo "  dev         Install development dependencies"
	@echo "  build       Build the package"
	@echo "  test        Test the package build"
	@echo "  clean       Clean build artifacts"
	@echo ""
	@echo "Publishing:"
	@echo "  patch       Publish a patch version (0.1.2 -> 0.1.3)"
	@echo "  minor       Publish a minor version (0.1.2 -> 0.2.0)"
	@echo "  major       Publish a major version (0.1.2 -> 1.0.0)"
	@echo "  dry-run     Test build without publishing"
	@echo ""
	@echo "Examples:"
	@echo "  make patch      # Quick patch release"
	@echo "  make dry-run    # Test before publishing"
	@echo "  make minor      # New feature release"

# Development
install:
	uv pip install -e .

dev:
	uv sync --dev

build:
	uv run hatch build

test: build
	uv run twine check dist/*

clean:
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Publishing
patch:
	@echo "🚀 Publishing patch version..."
	python publish.py --version patch

minor:
	@echo "🚀 Publishing minor version..."
	python publish.py --version minor

major:
	@echo "🚀 Publishing major version..."
	python publish.py --version major

dry-run:
	@echo "🧪 Testing build without publishing..."
	python publish.py --dry-run

# Quick publish (same as patch)
publish: patch
