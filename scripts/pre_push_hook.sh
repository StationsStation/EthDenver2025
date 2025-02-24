#! /usr/bin/env bash
set -e 

# Run lock command and store potential changes
poetry run autonomy packages lock

# Check for changes before proceeding
if [ -n "$(git status --porcelain packages/packages.json)" ]; then
    echo "Changes detected in packages/packages.json. Please commit the changes and push again."
    exit 1
fi

make clean-pyc && poetry run autonomy push-all

echo "Pre-push hook completed successfully."
