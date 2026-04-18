#!/usr/bin/env bash
set -euo pipefail

REPO_NAME="camp-picker"

cd "$(dirname "$0")"

if ! command -v git >/dev/null 2>&1; then
  echo "git is not installed or not on PATH."
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI (gh) is not installed or not on PATH."
  echo "Install gh and sign in once with: gh auth login"
  exit 1
fi

if [ ! -d .git ]; then
  echo "Initializing git repo..."
  git init
fi

if ! git config user.name >/dev/null 2>&1; then
  git config user.name "jikkujj"
fi

if ! git config user.email >/dev/null 2>&1; then
  git config user.email "jikkujj@users.noreply.github.com"
fi

git add .
if ! git commit -m "Prepare camp picker for deployment"; then
  echo "Nothing new to commit. Continuing."
fi

git branch -M main

if ! gh auth status >/dev/null 2>&1; then
  echo "You are not signed into GitHub CLI."
  echo "Run: gh auth login"
  exit 1
fi

gh repo create "$REPO_NAME" --public --source . --remote origin --push

echo "Done. Your code should now be on GitHub."
