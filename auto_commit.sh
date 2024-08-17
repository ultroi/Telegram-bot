#!/bin/bash

# Change to the directory of the script
cd "$(dirname "$0")"

# Check for uncommitted changes
if [[ -n $(git status -s) ]]; then
  # Stage all changes
  git add .

  # Commit changes with a message
  git commit -m "Automated commit: $(date)"

  # Push changes to the remote repository
  git push
else
  echo "No changes to commit."
fi
