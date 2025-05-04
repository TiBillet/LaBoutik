#!/bin/bash

# Change to the project root directory
cd "$(dirname "$0")/.."

# Run the test script using poetry
poetry run python epsonprinter/test_sunmi_printer.py

# If an argument is provided, pass it to the script
if [ $# -eq 1 ]; then
    poetry run python epsonprinter/test_sunmi_printer.py "$1"
fi