# Publishing Guide

This document explains how to publish new versions of the PayLink Python SDK to PyPI.

## Quick Start

The easiest way to publish is using the provided scripts:

```bash
# Publish a patch version (0.1.2 -> 0.1.3)
make patch

# Or use the Python script directly
python publish.py
```

## Available Publishing Methods

### 1. Using Make (Recommended)

```bash
# Patch version (bug fixes)
make patch

# Minor version (new features)
make minor

# Major version (breaking changes)
make major

# Test build without publishing
make dry-run
```

### 2. Using Python Script

```bash
# Patch version (default)
python publish.py

# Minor version
python publish.py --version minor

# Major version
python publish.py --version major

# Test build without publishing
python publish.py --dry-run
```

### 3. Using Shell Script

```bash
# Patch version
./publish.sh

# Minor version
./publish.sh --version minor

# Test build
./publish.sh --dry-run
```

### 4. Manual Process

If you prefer to do it manually:

```bash
# 1. Update version in pyproject.toml and paylink/__init__.py
# 2. Clean and build
rm -rf dist/
uv run hatch build

# 3. Check package
uv run twine check dist/*

# 4. Upload to PyPI
uv run twine upload dist/*
```

## Version Bumping

The scripts automatically handle version bumping:

- **Patch** (0.1.2 → 0.1.3): Bug fixes, documentation updates
- **Minor** (0.1.2 → 0.2.0): New features, backward compatible
- **Major** (0.1.2 → 1.0.0): Breaking changes

## Pre-Publishing Checklist

Before publishing, make sure:

- [ ] All changes are tested
- [ ] Version numbers are updated correctly
- [ ] CHANGELOG.md is updated (if you have one)
- [ ] README.md is up to date
- [ ] All tests pass
- [ ] Package builds without errors

## What the Scripts Do

1. **Check Git Status**: Warns about uncommitted changes
2. **Bump Version**: Updates version in both `pyproject.toml` and `paylink/__init__.py`
3. **Clean**: Removes old build artifacts
4. **Build**: Creates distribution packages using Hatch
5. **Check**: Validates the built packages
6. **Upload**: Publishes to PyPI (unless `--dry-run`)

## Troubleshooting

### Common Issues

1. **Version already exists**: The version number is already published on PyPI

   - Solution: The script will automatically bump the version

2. **Authentication failed**: PyPI credentials are incorrect

   - Solution: Check your `~/.pypirc` file

3. **Build failed**: Package has issues

   - Solution: Check the error messages and fix the code

4. **Git uncommitted changes**: You have uncommitted changes
   - Solution: Commit your changes or use `--force` (not recommended)

### Getting Help

- Check the script output for detailed error messages
- Use `--dry-run` to test without publishing
- Verify your PyPI credentials in `~/.pypirc`

## Configuration

The publishing process uses:

- **Build System**: Hatch (configured in `pyproject.toml`)
- **Upload Tool**: Twine
- **Credentials**: Stored in `~/.pypirc`

Make sure your `~/.pypirc` file contains:

```ini
[distutils]
  index-servers =
    pypi

[pypi]
  username = __token__
  password = pypi-YOUR_API_TOKEN_HERE
```

## Post-Publishing

After successful publishing:

1. Verify the package on PyPI: https://pypi.org/project/paylink/
2. Test installation: `pip install paylink`
3. Update any documentation that references the version
4. Consider creating a Git tag for the release

## Examples

### Typical Workflow

```bash
# 1. Make your changes and test them
git add .
git commit -m "Add new feature"

# 2. Publish a minor version
make minor

# 3. Verify on PyPI
open https://pypi.org/project/paylink/
```

### Testing Before Publishing

```bash
# Test the build process
make dry-run

# If everything looks good, publish
make patch
```

### Emergency Patch

```bash
# Quick bug fix release
make patch
```

This will automatically bump the patch version and publish immediately.
