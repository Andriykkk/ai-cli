#!/usr/bin/env python3
"""
Test runner script for AI CLI tools
"""

import subprocess
import sys
from pathlib import Path


def run_tests(test_type="all", verbose=False):
    """Run tests with specified parameters"""
    
    # Change to server directory
    server_dir = Path(__file__).parent
    
    # Build pytest command
    cmd = ["python", "-m", "pytest"]
    
    if verbose:
        cmd.append("-v")
    
    # Add test type filters
    if test_type == "functional":
        cmd.extend(["-m", "functional"])
    elif test_type == "security":
        cmd.extend(["-m", "security"])
    elif test_type == "integration":
        cmd.extend(["-m", "integration"])
    elif test_type == "unit":
        cmd.extend(["-m", "unit"])
    elif test_type == "fast":
        cmd.extend(["-m", "not slow"])
    elif test_type != "all":
        print(f"Unknown test type: {test_type}")
        print("Available types: all, functional, security, integration, unit, fast")
        return 1
    
    # Add test directory
    cmd.append("tests/")
    
    print(f"Running command: {' '.join(cmd)}")
    print(f"Working directory: {server_dir}")
    
    # Run tests
    try:
        result = subprocess.run(cmd, cwd=server_dir)
        return result.returncode
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        return 130
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run AI CLI tool tests")
    parser.add_argument(
        "test_type", 
        nargs="?", 
        default="all",
        choices=["all", "functional", "security", "integration", "unit", "fast"],
        help="Type of tests to run (default: all)"
    )
    parser.add_argument(
        "-v", "--verbose", 
        action="store_true",
        help="Run tests in verbose mode"
    )
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install test dependencies before running"
    )
    
    args = parser.parse_args()
    
    # Install dependencies if requested
    if args.install_deps:
        print("Installing test dependencies...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "-r", "test-requirements.txt"
            ])
        except subprocess.CalledProcessError as e:
            print(f"Failed to install dependencies: {e}")
            return 1
    
    # Run tests
    return run_tests(args.test_type, args.verbose)


if __name__ == "__main__":
    sys.exit(main())