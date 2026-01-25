#!/bin/bash
# Script to apply patches by calling apply_changes.py

set -e  # Exit on error

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Call the Python script
python3 "${SCRIPT_DIR}/apply_changes.py"

# Exit with the same exit code as the Python script
exit $?
