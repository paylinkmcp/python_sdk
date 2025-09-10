#!/bin/bash
# PayLink Python SDK Publishing Script (Shell version)

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
VERSION_TYPE="patch"
DRY_RUN=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --version)
            VERSION_TYPE="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help|-h)
            echo "PayLink Python SDK Publishing Script"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --version TYPE    Version bump type: patch, minor, major (default: patch)"
            echo "  --dry-run        Build and validate without uploading"
            echo "  --help, -h       Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                    # Bump patch version and publish"
            echo "  $0 --version minor    # Bump minor version and publish"
            echo "  $0 --dry-run          # Test build without publishing"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}🚀 PayLink SDK Publishing Script${NC}"
echo "========================================"

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}❌ Error: pyproject.toml not found. Please run this script from the project root.${NC}"
    exit 1
fi

# Check for uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${YELLOW}⚠️  Warning: You have uncommitted changes.${NC}"
    read -p "Do you want to continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Publishing cancelled."
        exit 1
    fi
fi

# Clean dist directory
echo -e "${BLUE}🧹 Cleaning dist directory...${NC}"
rm -rf dist/

# Build package
echo -e "${BLUE}🔨 Building package...${NC}"
uv run hatch build

# Check package
echo -e "${BLUE}🔍 Checking package...${NC}"
uv run twine check dist/*

if [ "$DRY_RUN" = true ]; then
    echo -e "${GREEN}✅ Dry run completed successfully!${NC}"
    echo "Files ready for upload:"
    ls -la dist/
else
    # Upload to PyPI
    echo -e "${BLUE}📤 Uploading to PyPI...${NC}"
    uv run twine upload dist/*
    
    echo -e "${GREEN}✅ Package published successfully!${NC}"
    echo -e "${GREEN}Install with: pip install paylink${NC}"
fi
