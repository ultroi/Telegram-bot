#!/bin/bash

# Change to the directory of the script
cd "$(dirname "$0")"

# Pull the latest changes from the remote repository
git pull origin main

# Check for uncommitted changes
if [[ -n $(git status -s) ]]; then
  # Stage all changes
  git add .

  # Commit changes with a message
  git commit -m "Automated commit: $(date)"

  # Push changes to the remote repository
  git push origin main
else
  echo "No changes to commit."
fi
