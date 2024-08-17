#!/bin/bash

# Navigate to your repository
cd /path/to/your/repository

# Set nano as the default editor if it's not set already
git config --global core.editor "nano"

# Pull the latest changes from the remote repository
git pull origin main

# Check if there are merge conflicts
if [ $? -ne 0 ]; then
  echo "Merge conflicts detected. Please resolve them manually."
  exit 1
fi

# Stage all changes
git add .

# Commit changes
git commit -m "Automated commit after resolving conflicts"

# Push changes to the remote repository
git push origin main
