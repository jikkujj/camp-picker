@echo off
setlocal

set "REPO_NAME=camp-picker"

cd /d "%~dp0"

where git >nul 2>&1
if errorlevel 1 (
  echo Git is not installed or not on PATH.
  exit /b 1
)

where gh >nul 2>&1
if errorlevel 1 (
  echo GitHub CLI ^(gh^) is not installed or not on PATH.
  echo Install gh, sign in once with: gh auth login
  exit /b 1
)

git status --short >nul 2>&1
if errorlevel 1 (
  echo This folder does not look like a git repo. Initializing...
  git init || exit /b 1
)

git add .
git commit -m "Prepare camp picker for deployment"
if errorlevel 1 (
  echo Commit step may have had nothing new to commit. Continuing.
)

git branch -M main

gh auth status >nul 2>&1
if errorlevel 1 (
  echo You are not signed into GitHub CLI.
  echo Run: gh auth login
  exit /b 1
)

gh repo create %REPO_NAME% --public --source . --remote origin --push --confirm
if errorlevel 1 (
  echo Repo creation or push failed.
  exit /b 1
)

echo Done. Your code should now be on GitHub.
endlocal
