#!/usr/bin/env python3
"""
PayLink Python SDK Publishing Script

This script automates the process of publishing the PayLink SDK to PyPI.
It handles version bumping, building, testing, and uploading.

Usage:
    python publish.py [--version TYPE] [--dry-run] [--help]

Options:
    --version TYPE    Version bump type: patch, minor, major (default: patch)
    --dry-run        Build and validate without uploading
    --help           Show this help message

Examples:
    python publish.py                    # Bump patch version and publish
    python publish.py --version minor    # Bump minor version and publish
    python publish.py --dry-run          # Test build without publishing
"""

import argparse
import re
import subprocess
import sys
import os
from pathlib import Path


class PayLinkPublisher:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.pyproject_path = self.project_root / "pyproject.toml"
        self.init_path = self.project_root / "paylink" / "__init__.py"

    def run_command(self, command, check=True):
        """Run a shell command and return the result."""
        print(f"Running: {' '.join(command)}")
        result = subprocess.run(
            command, capture_output=True, text=True, cwd=self.project_root
        )

        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        if check and result.returncode != 0:
            print(f"Command failed with exit code {result.returncode}")
            sys.exit(1)

        return result

    def get_current_version(self):
        """Get the current version from pyproject.toml."""
        with open(self.pyproject_path, "r") as f:
            content = f.read()
            match = re.search(r'version = "([^"]+)"', content)
            if match:
                return match.group(1)
        raise ValueError("Could not find version in pyproject.toml")

    def bump_version(self, version_type):
        """Bump the version number in both pyproject.toml and __init__.py."""
        current_version = self.get_current_version()
        print(f"Current version: {current_version}")

        # Parse version
        parts = current_version.split(".")
        if len(parts) != 3:
            raise ValueError(f"Invalid version format: {current_version}")

        major, minor, patch = map(int, parts)

        # Bump version
        if version_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif version_type == "minor":
            minor += 1
            patch = 0
        elif version_type == "patch":
            patch += 1
        else:
            raise ValueError(f"Invalid version type: {version_type}")

        new_version = f"{major}.{minor}.{patch}"
        print(f"New version: {new_version}")

        # Update pyproject.toml
        with open(self.pyproject_path, "r") as f:
            content = f.read()
        content = re.sub(r'version = "[^"]+"', f'version = "{new_version}"', content)
        with open(self.pyproject_path, "w") as f:
            f.write(content)

        # Update __init__.py
        with open(self.init_path, "r") as f:
            content = f.read()
        content = re.sub(
            r'__version__ = "[^"]+"', f'__version__ = "{new_version}"', content
        )
        with open(self.init_path, "w") as f:
            f.write(content)

        return new_version

    def clean_dist(self):
        """Clean the dist directory."""
        dist_dir = self.project_root / "dist"
        if dist_dir.exists():
            print("Cleaning dist directory...")
            import shutil

            shutil.rmtree(dist_dir)

    def build_package(self):
        """Build the package using hatch."""
        print("Building package...")
        self.run_command(["uv", "run", "hatch", "build"])

    def check_package(self):
        """Check the built package for issues."""
        print("Checking package...")
        self.run_command(["uv", "run", "twine", "check", "dist/*"])

    def upload_package(self):
        """Upload the package to PyPI."""
        print("Uploading to PyPI...")
        self.run_command(["uv", "run", "twine", "upload", "dist/*"])

    def validate_git_status(self):
        """Check if there are uncommitted changes."""
        result = self.run_command(["git", "status", "--porcelain"], check=False)
        if result.stdout.strip():
            print("Warning: You have uncommitted changes.")
            response = input("Do you want to continue? (y/N): ")
            if response.lower() != "y":
                print("Publishing cancelled.")
                sys.exit(1)

    def publish(self, version_type="patch", dry_run=False):
        """Main publishing workflow."""
        print("🚀 PayLink SDK Publishing Script")
        print("=" * 40)

        try:
            # Validate git status
            self.validate_git_status()

            # Bump version
            new_version = self.bump_version(version_type)

            # Clean and build
            self.clean_dist()
            self.build_package()

            # Check package
            self.check_package()

            if dry_run:
                print("✅ Dry run completed successfully!")
                print(f"Package would be published as version {new_version}")
                print("Files ready for upload:")
                dist_dir = self.project_root / "dist"
                for file in dist_dir.glob("*"):
                    print(f"  - {file.name}")
            else:
                # Upload to PyPI
                self.upload_package()
                print("✅ Package published successfully!")
                print(f"Version {new_version} is now available on PyPI")
                print(f"Install with: pip install paylink")
                print(f"PyPI URL: https://pypi.org/project/paylink/{new_version}/")

        except Exception as e:
            print(f"❌ Error: {e}")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Publish PayLink Python SDK to PyPI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--version",
        choices=["patch", "minor", "major"],
        default="patch",
        help="Version bump type (default: patch)",
    )

    parser.add_argument(
        "--dry-run", action="store_true", help="Build and validate without uploading"
    )

    args = parser.parse_args()

    publisher = PayLinkPublisher()
    publisher.publish(version_type=args.version, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
