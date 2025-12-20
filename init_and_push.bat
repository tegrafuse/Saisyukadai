@echo off
REM init_and_push.bat
REM Usage: init_and_push.bat [REMOTE_URL] [BRANCH]
REM Defaults: REMOTE_URL=https://github.com/tegrafuse/Saisyukadai.git, BRANCH=main

SETLOCAL EnableDelayedExpansion

IF "%~1"=="" (
  SET REMOTE_URL=https://github.com/tegrafuse/Saisyukadai.git
) ELSE (
  SET REMOTE_URL=%~1
)

IF "%~2"=="" (
  SET BRANCH=main
) ELSE (
  SET BRANCH=%~2
)

echo Initializing git repository (if not already initialized)...
if not exist .git (
  git init
) else (
  echo Repository already initialized.
)

REM Ensure remote is set to provided URL
git remote remove origin 2>nul
git remote add origin %REMOTE_URL%

echo Adding files...
git add -A

SET /P MSG=Initial commit message (default: "Initial commit"): 
IF "%MSG%"=="" SET MSG=Initial commit

git commit -m "%MSG%" || (
  echo Commit failed or no changes to commit.
)

REM Set branch name (create/rename locally) and push
git branch -M %BRANCH%
git push -u origin %BRANCH%

ENDLOCAL
pause